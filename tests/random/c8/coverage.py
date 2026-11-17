#!/usr/bin/env python3
"""What C8 exercised (spec §8 coverage). Owner: Beru. Model-only: replays a C8 run's programs through
ref/pins6502.py with the inputs the testbench recorded (pins.txt) and counts spec behaviours. The RTL
agreement itself is C8's log; this says what that agreement covered.
Usage: tests/random/c8/coverage.py --out DIR --seed S --nprog N    (the same values as the C8 run)
"""
import argparse, collections, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run
R, P = run.R, run.P

INDEXED_READ = {"abx", "aby", "izy"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--nprog", type=int, required=True)
    a = ap.parse_args()
    ops = collections.Counter()
    cov = collections.Counter()                     # behaviour -> count
    orig_step, orig_int = R.CPU.step, R.CPU.interrupt

    def step(self):
        pc = self.pc
        op = self.read(pc)
        d, i_before = self.d, self.i
        cyc = orig_step(self)
        m, mode = R.OPS[op]
        ops[op] += 1
        n = len(cyc)
        if m in R.READ_OPS and mode in INDEXED_READ:
            cov[f"read {mode} {'page cross' if n > {'abx': 4, 'aby': 4, 'izy': 5}[mode] else 'no cross'}"] += 1
        if m in R.STORE_OPS and mode in INDEXED_READ:
            cov[f"store {mode} (dummy read always)"] += 1
        if m in R.RMW_OPS and mode != "acc":
            cov[f"RMW {mode} (double write)"] += 1
        if mode in ("zpx", "zpy", "izx") or mode == "izy":
            pass
        if m in R.BRANCH:
            kind = {2: "not taken", 3: "taken, same page", 4: "taken, page cross"}[n]
            cov[f"{m} {kind}"] += 1
        if m == "JMP" and mode == "ind":
            cov["JMP (ind) at $xxFF (wrap)" if self.read((pc + 1) & 0xFFFF) == 0xFF else "JMP (ind) no wrap"] += 1
        if m in ("ADC", "SBC"):
            cov[f"{m} decimal (D = 1)" if d else f"{m} binary"] += 1
        if m == "BRK":
            cov["BRK"] += 1
        return cyc

    R.CPU.step = step

    # §6 poll rule, from pins6502's trace (one event per poll, one per sequence start)
    pend_cli = [False]

    def trace(e):
        if "seq_start" in e:
            cov[f"{e['seq_start']} sequence"] += 1
            if e["nmi_pending"] is not None:
                cov["NMI pending while a sequence runs (taken after the first handler instruction)"] += 1
            return
        m, d = e["op"][0], e["decision"]
        irq_low = e["irq"] == 0
        if pend_cli[0] and d == "IRQ":
            cov["IRQ one instruction after CLI/PLP cleared I (old-I latency)"] += 1
        pend_cli[0] = False
        if irq_low and m in ("CLI", "PLP") and e["i_before"] == 1 and e["i_after"] == 0:
            cov[f"{m} 1->0 with irq_n low: not taken right after (old I)"] += d != "IRQ"
            pend_cli[0] = True
        if irq_low and m in ("SEI", "PLP") and e["i_before"] == 0 and e["i_after"] == 1 and d == "IRQ":
            cov[f"{m} 0->1 with irq_n low: one IRQ right after (old I)"] += 1
        if irq_low and m == "RTI" and e["i_after"] == 0 and d == "IRQ":
            cov["RTI pulling I = 0 with irq_n low: IRQ right after (new I)"] += 1
        if irq_low and m == "RTI" and e["i_before"] == 0 and e["i_after"] == 1 and d is None:
            cov["RTI pulling I = 1 with irq_n low: no IRQ (new I)"] += 1
        np_ = e["nmi_pending"]
        if np_ is not None and np_ > e["edge"]:
            if m in R.BRANCH and e["k"] == 3 and np_ <= e["ends"][1]:
                cov["NMI deferred by a taken no-cross branch's early poll (branch delay)"] += 1
            elif np_ == e["edge"] + 1:
                cov["NMI detected at the poll edge itself: deferred to the next instruction"] += 1
        if d == "NMI" and irq_low and e["i_seen"] == 0:
            cov["NMI and IRQ at the same poll: NMI wins"] += 1
        if e["poll"] >= 2 and e["ends"][e["poll"] - 1] - e["ends"][e["poll"] - 2] > 1:
            cov["poll cycle repeated by RDY (poll at its last repetition)"] += 1

    orig_init = P.PinModel.__init__

    def init(self, *aa, **kk):
        orig_init(self, *aa, **kk)
        self.trace = trace
    P.PinModel.__init__ = init

    # RDY: held read cycles by kind
    orig_emit = P.PinModel._emit

    def emit(self, cycles, ends):
        for a_, rw, d_, sync in cycles:
            if rw == 1 and not self.rdy(self.n):
                cov["RDY hold on an opcode fetch (sync)" if sync else "RDY hold on a non-fetch read"] += 1
            if rw == 0 and not self.rdy(self.n):
                cov["RDY low during a write (ignored)"] += 1
        yield from orig_emit(self, cycles, ends)
    P.PinModel._emit = emit

    for p in range(a.nprog):
        mem = run.gen(random.Random(a.seed * 100003 + p))
        lines = [l.split() for l in open(f"{a.out}/prog{p}/pins.txt")]
        run.compare(mem, lines)

    doc = sorted(R.OPS)
    missing_ops = [f"{b:02X}" for b in doc if not ops[b]]
    want = ([f"read {m} {k}" for m in ("abx", "aby", "izy") for k in ("page cross", "no cross")]
            + [f"store {m} (dummy read always)" for m in ("abx", "aby", "izy")]
            + [f"RMW {m} (double write)" for m in ("zp", "zpx", "abs", "abx")]
            + [f"{b} {k}" for b in R.BRANCH for k in ("not taken", "taken, same page", "taken, page cross")]
            + ["JMP (ind) at $xxFF (wrap)", "JMP (ind) no wrap", "ADC decimal (D = 1)", "SBC decimal (D = 1)",
               "ADC binary", "SBC binary", "BRK", "IRQ sequence", "NMI sequence",
               "RDY hold on an opcode fetch (sync)", "RDY hold on a non-fetch read", "RDY low during a write (ignored)",
               "CLI 1->0 with irq_n low: not taken right after (old I)",
               "PLP 1->0 with irq_n low: not taken right after (old I)",
               "IRQ one instruction after CLI/PLP cleared I (old-I latency)",
               "SEI 0->1 with irq_n low: one IRQ right after (old I)",
               "PLP 0->1 with irq_n low: one IRQ right after (old I)",
               "RTI pulling I = 0 with irq_n low: IRQ right after (new I)",
               "RTI pulling I = 1 with irq_n low: no IRQ (new I)",
               "NMI deferred by a taken no-cross branch's early poll (branch delay)",
               "NMI detected at the poll edge itself: deferred to the next instruction",
               "NMI and IRQ at the same poll: NMI wins",
               "NMI pending while a sequence runs (taken after the first handler instruction)",
               "poll cycle repeated by RDY (poll at its last repetition)"])
    print(f"opcodes executed: {len(doc) - len(missing_ops)}/151; never: {' '.join(missing_ops) or 'none'}")
    for k in want:
        print(f"  {cov[k]:>9}  {k}")
    others = sorted(k for k in cov if k not in want)
    for k in others:
        print(f"  {cov[k]:>9}  {k}")
    miss = [k for k in want if not cov[k]]
    print(f"behaviours listed: {len(want)}, not exercised: {len(miss)}" + (": " + "; ".join(miss) if miss else ""))


if __name__ == "__main__":
    main()
