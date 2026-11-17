#!/usr/bin/env python3
"""6502 pin model (Beru, chip-6502#6): ref6502's bus cycles with RDY holds and IRQ/NMI, one Pins per
clock, for C8. Written from docs/spec.md; open questions are in chip-6502#25 and each is one flag here.

Inputs are functions of the cycle number n (the testbench logs what it drove in each cycle and the
model replays it): rdy(n), irq_n(n), nmi_n(n).
- RDY (§2, §4.0): a read cycle with rdy = 0 repeats with the same pins until a cycle with rdy = 1.
  Write cycles ignore rdy.
- IRQ/NMI (§6 and #25 Q1, reading A): the lines are sampled in an instruction's first cycle (they only
  change at the edge that starts a fetch, §6 stimulus rule) and act after that instruction completes:
  the next cycle is the interrupt sequence's T0 (A.5.4). IRQ needs irq_n = 0 and I = 0; I is the value
  after the instruction (#25 Q2, flag IRQ_OLD_I to use the value before). NMI is a falling edge; it
  wins over IRQ when both are pending (the stimulus rule keeps them out of the same boundary anyway).
- During an interrupt sequence the lines are ignored (#25 Q4); the next instruction samples them anew.
Usage: python3 ref/pins6502.py   (selftest)
"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref6502 as R

Pins = collections.namedtuple("Pins", "a rw sync d_oe d_out")
IRQ_OLD_I = False          # chip-6502#25 Q2: False = decide with I after the instruction


class PinModel:
    def __init__(self, cpu, rdy=lambda n: 1, irq_n=lambda n: 1, nmi_n=lambda n: 1):
        self.cpu, self.rdy, self.irq_n, self.nmi_n = cpu, rdy, irq_n, nmi_n
        self.n = 0                    # next cycle number
        self.nmi_prev = 1             # nmi_n as last sampled at an instruction
        self.instructions = 0
        self.interrupts = collections.Counter()

    def _emit(self, cycles):
        for a, rw, d, sync in cycles:
            p = Pins(a, rw, sync, 1 - rw, d if rw == 0 else None)
            while rw == 1 and not self.rdy(self.n):          # RDY holds a read: same pins again
                yield p
                self.n += 1
            yield p
            self.n += 1

    def states(self):
        """Generator of Pins, one per cycle, forever (or until Undocumented)."""
        c = self.cpu
        while True:
            n0 = self.n
            irq, nmi = self.irq_n(n0), self.nmi_n(n0)
            nmi_edge = self.nmi_prev == 1 and nmi == 0
            self.nmi_prev = nmi
            i_before = c.i
            yield from self._emit(c.step())
            self.instructions += 1
            i_dec = i_before if IRQ_OLD_I else c.i
            if nmi_edge:
                self.interrupts["NMI"] += 1
                yield from self._emit(c.interrupt(nmi=True))
            elif irq == 0 and i_dec == 0:
                self.interrupts["IRQ"] += 1
                yield from self._emit(c.interrupt(nmi=False))


# ---------------------------------------------------------------- selftest
def _run(prog, org=0x0200, n=40, **inputs):
    mem = bytearray(65536)
    mem[org:org + len(prog)] = bytes(prog)
    mem[0xFFFE], mem[0xFFFF] = 0x00, 0x30            # IRQ/BRK vector 3000
    mem[0xFFFA], mem[0xFFFB] = 0x00, 0x40            # NMI vector 4000
    mem[0x3000] = mem[0x4000] = 0xEA                 # NOPs in the handlers
    c = R.CPU(mem.__getitem__, mem.__setitem__)
    c.pc, c.s, c.i = org, 0xFF, 0
    pm = PinModel(c, **inputs)
    g = pm.states()
    return [next(g) for _ in range(n)], pm, c, mem


def selftest():
    fails = 0

    def check(cond, msg):
        nonlocal fails
        if not cond:
            fails += 1; print("FAIL", msg)
    # 1. RDY: LDA $1234 (4 cycles) with rdy = 0 in cycles 1-2 → cycle 1 (operand read at 0201) repeats 3x
    pins, *_ = _run([0xAD, 0x34, 0x12, 0xEA], n=7, rdy=lambda n: 0 if n in (1, 2) else 1)
    check([p.a for p in pins] == [0x200, 0x201, 0x201, 0x201, 0x202, 0x1234, 0x203], f"RDY read hold: {[hex(p.a) for p in pins]}")
    # 2. RDY ignored on a write: STA $1234 with rdy = 0 in cycle 3 (the write) → no repeat; then the next
    #    read (the following fetch, cycle 4) is held instead
    pins, *_ = _run([0x8D, 0x34, 0x12, 0xEA], n=6, rdy=lambda n: 0 if n in (3, 4) else 1)
    check([(p.a, p.rw) for p in pins] == [(0x200, 1), (0x201, 1), (0x202, 1), (0x1234, 0), (0x203, 1), (0x203, 1)],
          f"RDY on write: {[(hex(p.a), p.rw) for p in pins]}")
    # 3. IRQ low from cycle 0 (I = 0): NOP completes (2 cycles), then the 7-cycle sequence, vector 3000
    pins, pm, c, mem = _run([0xEA, 0xEA], n=10, irq_n=lambda n: 0 if n < 20 else 1)
    check([p.a for p in pins[:10]] == [0x200, 0x201, 0x201, 0x201, 0x1FF, 0x1FE, 0x1FD, 0xFFFE, 0xFFFF, 0x3000]
          and pins[2].sync == 1 and pins[9].sync == 1, f"IRQ after NOP: {[hex(p.a) for p in pins]}")
    check(mem[0x1FD] & 0x30 == 0x20 and mem[0x1FF] == 0x02 and mem[0x1FE] == 0x01, f"IRQ pushes PC 0201, B=0: {mem[0x1FD]:02X}")
    # 4. IRQ masked by I = 1 (SEI first): no interrupt while I = 1
    pins, pm, *_ = _run([0x78, 0xEA, 0xEA, 0xEA], n=8, irq_n=lambda n: 0 if n >= 2 else 1)
    check(pm.interrupts["IRQ"] == 0, f"IRQ masked: {pm.interrupts}")
    # 5. NMI falling edge at the second instruction's boundary (cycle 2): taken after it, vector 4000
    pins, pm, *_ = _run([0xEA, 0xEA, 0xEA], n=12, nmi_n=lambda n: 0 if n >= 2 else 1)
    check([p.a for p in pins[4:12]] == [0x202, 0x202, 0x1FF, 0x1FE, 0x1FD, 0xFFFA, 0xFFFB, 0x4000] and pm.interrupts["NMI"] == 1,
          f"NMI: {[hex(p.a) for p in pins]}")
    # 6. NMI held low: only one interrupt (edge), even with I = 0 and many instructions
    # (nmi_n already low when the model starts isn't specified; C8 holds nmi_n = 1 through reset.)
    pins, pm, *_ = _run([0xEA] * 30, n=60, nmi_n=lambda n: 0 if n >= 2 else 1)
    check(pm.interrupts["NMI"] == 1, f"NMI held low: one edge, {pm.interrupts}")
    print(("PASS" if not fails else f"FAIL ({fails})") + " pins6502 selftest: RDY on reads/writes, IRQ, I mask, NMI edge")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if selftest() else 0)
