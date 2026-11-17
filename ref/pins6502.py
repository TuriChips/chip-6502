#!/usr/bin/env python3
"""6502 pin model (Beru, chip-6502#6): ref6502's bus cycles with RDY holds and IRQ/NMI, one Pins per
clock, for C8. Written from docs/spec.md; the interrupt rule is §6's poll-rule Decision (spec PR #27,
answering chip-6502#25).

Inputs are functions of the cycle number n: the value the testbench drove during cycle n, which is the
value "sampled at the edge that ends cycle n". rdy(n), irq_n(n), nmi_n(n).
- RDY (§2, §4.0): a read cycle with rdy = 0 repeats with the same pins until a cycle with rdy = 1.
  Write cycles ignore rdy.
- Poll (§6 rule 1): an instruction of k cycles polls once, at the edge ending its cycle k-1 (the last
  repetition, under RDY); a taken branch without a page cross (3 cycles) polls at the end of cycle 1.
- What the poll sees (rule 2): irq_n at that edge, and I as it stands then: CLI, SEI and PLP change I
  after their poll (old I), RTI before it (new I); no other instruction changes I.
- NMI (rule 3): the detector runs at every edge; pending when sampled 0 after 1, visible to polls from
  the next edge on; cleared when a poll takes it. NMI wins over IRQ (rule 4).
- BRK and the IRQ/NMI/reset sequences don't poll (rule 5): the first instruction at the vector always
  runs. A sequence's vector is fixed when it starts (no hijack).
Usage: python3 ref/pins6502.py   (selftest)
"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref6502 as R

Pins = collections.namedtuple("Pins", "a rw sync d_oe d_out")
OLD_I = {"CLI", "SEI", "PLP"}       # judged by I before the instruction (§6 rule 2); RTI by the new I


class PinModel:
    def __init__(self, cpu, rdy=lambda n: 1, irq_n=lambda n: 1, nmi_n=lambda n: 1):
        self.cpu, self.rdy, self.irq_n, self.nmi_n = cpu, rdy, irq_n, nmi_n
        self.n = 0                    # next cycle number
        self.nmi_last = 1             # nmi_n sampled at the previous edge
        self.nmi_pending = None       # first cycle whose closing edge may see the pending NMI, or None
        self.instructions = 0
        self.interrupts = collections.Counter()
        self.trace = None             # optional callback(dict) at each poll, for coverage (tests/random/c8/coverage.py)

    def clear_nmi(self, last=1):
        """Reset (§6 rule 6): no pending NMI; last = nmi_n as sampled before the restart."""
        self.nmi_pending, self.nmi_last = None, last

    def _edge(self):
        """Edge at the end of cycle self.n: the NMI detector."""
        v = self.nmi_n(self.n)
        if self.nmi_last == 1 and v == 0 and self.nmi_pending is None:
            self.nmi_pending = self.n + 1          # visible from the next edge on
        self.nmi_last = v

    def _emit(self, cycles, ends):
        """Yield Pins for each bus cycle (RDY repeats included); ends[k] = global number of the last
        repetition of cycle k."""
        for a, rw, d, sync in cycles:
            p = Pins(a, rw, sync, 1 - rw, d if rw == 0 else None)
            while rw == 1 and not self.rdy(self.n):          # RDY holds a read: same pins again
                yield p
                self._edge(); self.n += 1
            yield p
            ends.append(self.n)
            self._edge(); self.n += 1

    def _sequence(self, nmi):
        self.interrupts["NMI" if nmi else "IRQ"] += 1
        if self.trace:
            self.trace(dict(seq_start="NMI" if nmi else "IRQ", n=self.n, nmi_pending=self.nmi_pending))
        yield from self._emit(self.cpu.interrupt(nmi=nmi), [])

    def states(self):
        """Generator of Pins, one per cycle, forever (or until Undocumented)."""
        c = self.cpu
        while True:
            i_before = c.i
            pc = c.pc
            op = R.OPS.get(c.read(pc))
            ends = []
            yield from self._emit(c.step(), ends)
            self.instructions += 1
            if op is None or op[0] == "BRK":               # BRK is a sequence: no poll (rule 5)
                continue
            k = len(ends)
            poll = 1 if (op[0] in R.BRANCH and k == 3) else k - 1      # cycle numbers from 1
            edge = ends[poll - 1]                          # global cycle whose closing edge polls
            i_seen = i_before if op[0] in OLD_I else c.i
            nmi_vis = self.nmi_pending is not None and self.nmi_pending <= edge
            irq_take = self.irq_n(edge) == 0 and i_seen == 0
            if self.trace:                                 # coverage only; no effect on the model
                self.trace(dict(op=op, k=k, ends=ends, poll=poll, edge=edge, i_before=i_before, i_after=c.i,
                                i_seen=i_seen, irq=self.irq_n(edge), nmi_pending=self.nmi_pending,
                                decision="NMI" if nmi_vis else "IRQ" if irq_take else None))
            if nmi_vis:
                self.nmi_pending = None
                yield from self._sequence(nmi=True)
            elif irq_take:
                yield from self._sequence(nmi=False)


# ---------------------------------------------------------------- selftest
def _run(prog, org=0x0200, n=40, i=0, s=0xFF, z=1, setup=None, **inputs):
    """The NMI detector starts with nmi_n sampled 1 before cycle 0, so a line low from cycle 0 is an
    edge at the end of cycle 0 (as after reset with nmi_n held 1, then lowered at the first fetch)."""
    mem = bytearray(65536)
    mem[org:org + len(prog)] = bytes(prog)
    mem[0xFFFE], mem[0xFFFF] = 0x00, 0x30            # IRQ/BRK vector 3000
    mem[0xFFFA], mem[0xFFFB] = 0x00, 0x40            # NMI vector 4000
    mem[0x3000] = mem[0x4000] = 0xEA                 # NOPs in the handlers
    c = R.CPU(mem.__getitem__, mem.__setitem__)
    if setup: setup(mem)
    c.pc, c.s, c.i, c.z = org, s, i, z
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
    # 5. NMI falls at the 2nd NOP's first edge (cycle 2): detected at the end of cycle 2, visible from 3;
    #    that NOP polls at the end of cycle 2 (its cycle 1) → not yet; the 3rd NOP (cycles 4-5) polls at 4 → NMI
    pins, pm, *_ = _run([0xEA] * 4, n=14, nmi_n=lambda n: 0 if n >= 2 else 1)
    check([p.a for p in pins[6:14]] == [0x203, 0x203, 0x1FF, 0x1FE, 0x1FD, 0xFFFA, 0xFFFB, 0x4000] and pm.interrupts["NMI"] == 1,
          f"NMI visibility: {[hex(p.a) for p in pins]}")
    # 5b. same, but a 3-cycle instruction (LDA zp) sees it: NMI right after it
    pins, pm, *_ = _run([0xEA, 0xA5, 0x10, 0xEA, 0xEA], n=13, nmi_n=lambda n: 0 if n >= 2 else 1)
    check([p.a for p in pins[5:7]] == [0x203, 0x203] and pins[7].a == 0x1FF, f"NMI after a 3-cycle instr: {[hex(p.a) for p in pins]}")
    # 6. NMI held low: one edge, one NMI
    pins, pm, *_ = _run([0xEA] * 30, n=60, nmi_n=lambda n: 0 if n >= 2 else 1)
    check(pm.interrupts["NMI"] == 1, f"NMI held low: one edge, {pm.interrupts}")
    # 7. CLI with irq_n low (I = 1 before): CLI judged by old I → no IRQ; the next NOP sees I = 0 → IRQ after it
    pins, pm, c, mem = _run([0x58, 0xEA, 0xEA], n=12, irq_n=lambda n: 0, i=1)
    check([p.a for p in pins[4:6]] == [0x202, 0x202] and pins[6].a == 0x1FF, f"CLI latency: {[hex(p.a) for p in pins]}")
    # 8. SEI with irq_n low (I = 0 before): judged by old I → one IRQ right after SEI, pushed P has I = 1
    pins, pm, c, mem = _run([0x78, 0xEA], n=12, irq_n=lambda n: 0)
    check(pins[2].a == 0x201 and pins[4].a == 0x1FF and mem[0x1FD] & 0x04 and pm.interrupts["IRQ"] == 1,
          f"SEI: {[hex(p.a) for p in pins]} P={mem[0x1FD]:02X} {pm.interrupts}")
    # 9. RTI pulling I = 0 with irq_n low: judged by the new I → IRQ right after RTI
    #    stack (S=FC): P=00 at 1FD, PCL 00, PCH 05 → returns to 0500 (NOP)
    def rti_mem(mem): mem[0x1FD], mem[0x1FE], mem[0x1FF] = 0x00, 0x00, 0x05; mem[0x500] = 0xEA
    pins, pm, c, mem = _run([0x40], n=14, irq_n=lambda n: 0, i=1, s=0xFC, setup=rti_mem)
    check(pins[6].a == 0x500 and pins[7].a == 0x500 and pins[8].a == 0x1FF, f"RTI new I: {[hex(p.a) for p in pins]}")
    # 10. branch delay, NMI falling at a taken no-cross BNE's first edge: BNE polls at the end of its cycle 1
    #     → not visible; the NOP at the target polls → NMI after it. With a page cross (4 cycles) → right after.
    pins, pm, *_ = _run([0xD0, 0x02, 0xEA, 0xEA, 0xEA, 0xEA], n=14, nmi_n=lambda n: 0, z=0)
    check([p.a for p in pins[3:7]] == [0x204, 0x205, 0x205, 0x205] and pins[7].a == 0x1FF, f"branch delay: {[hex(p.a) for p in pins]}")
    pins, pm, *_ = _run([0xD0, 0x7F], org=0x0280, n=12, nmi_n=lambda n: 0, z=0)
    check([p.a for p in pins[:6]] == [0x280, 0x281, 0x282, 0x201, 0x301, 0x301] and pins[6].a == 0x1FF,
          f"branch with page cross: {[hex(p.a) for p in pins]}")
    # 11. NMI and IRQ at the same poll: NMI wins; then the first NMI-handler instruction runs, then the IRQ?
    #     (no: the NMI sequence sets I, so no IRQ until the handler clears it)
    pins, pm, *_ = _run([0xEA, 0xA5, 0x10, 0xEA], n=14, irq_n=lambda n: 0 if n >= 2 else 1, nmi_n=lambda n: 0 if n >= 2 else 1)
    check(pins[10].a == 0xFFFA and pm.interrupts == {"NMI": 1}, f"NMI over IRQ: {[hex(p.a) for p in pins]} {pm.interrupts}")
    # 12. NMI falling at an IRQ sequence's first edge: the sequence keeps vector FFFE (no hijack), the first
    #     IRQ-handler instruction (NOP at 3000) runs, then the NMI
    pins, pm, *_ = _run([0xEA, 0xEA], n=20, irq_n=lambda n: 0, nmi_n=lambda n: 0 if n >= 2 else 1)
    check([p.a for p in pins[7:12]] == [0xFFFE, 0xFFFF, 0x3000, 0x3001, 0x3001] and pins[16].a == 0xFFFA,
          f"no hijack, first handler instruction: {[hex(p.a) for p in pins]}")
    # 13. RDY repeats the poll cycle: NMI falls at a NOP's first edge, rdy = 0 in that cycle once → the poll
    #     moves to the end of the repetition, where the NMI is visible → NMI right after this NOP
    pins, pm, *_ = _run([0xEA, 0xEA, 0xEA], n=12, nmi_n=lambda n: 0, rdy=lambda n: 0 if n == 0 else 1)
    check([p.a for p in pins[:5]] == [0x200, 0x200, 0x201, 0x201, 0x201] and pins[5].a == 0x1FF, f"RDY moves the poll: {[hex(p.a) for p in pins]}")
    print(("PASS" if not fails else f"FAIL ({fails})") + " pins6502 selftest: RDY, IRQ/I mask, §6 poll rule (NMI visibility, CLI/SEI/RTI, branch delay, priority, no hijack, RDY)")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if selftest() else 0)
