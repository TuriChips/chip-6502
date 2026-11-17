// C8 with mid-run resets (Beru, chip-6502#6): as tb.sv, plus res_n pulled low at random cycles for 8-12
// cycles (spec §5: >= 8), with rdy = 1 from then until reset cycle 8 (#40) and irq_n = nmi_n = 1 while low.
// At each reset the RAM is dumped (after the edge ending the first res_n = 0 cycle) to <dir>/prog<p>/mem_rst<k>.hex.
// Original header:
// C8 testbench: runs random programs on the RTL m6502 and dumps every cycle's pins
// and inputs; tests/random/c8/run.py replays the inputs through ref/pins6502.py and compares.
// Memory is the testbench's own 64 KiB array (combinational read, write at the clock edge when rw = 0).
// Stimulus (spec §6, §2, §5): rdy random in any cycle from reset cycle 8 on (1 before, #40); irq_n / nmi_n change only in a cycle with sync = 1
// (set right after the edge that starts it), nmi_n stays put for >= 2 cycles (it can only change at
// sync cycles, and every instruction or sequence is >= 2 cycles). res_n = 0 for 10 cycles, inputs high.
// Plusargs: +dir= +nprog= +nst= +seed= +rdy= (percent of cycles with rdy = 0) +irq= +nmi= (per-mille
// chance of toggling the line at a sync cycle).
// Dump: <dir>/prog<p>/pins.txt, one line per cycle: a rw sync d_oe d_out rdy irq_n nmi_n res_n
`timescale 1ns/1ps
module tb;
    reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1;
    reg [7:0] mem [0:65535];
    wire [15:0] a; wire [7:0] d_out; wire d_oe, rw, sync;
    wire [7:0] d_in = mem[a];
    m6502 dut(.clk(clk), .res_n(res_n), .a(a), .d_in(d_in), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync),
              .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(1'b1));
    always #5 clk = ~clk;

    integer fd, p, n, nprog, nst, seed, rdy_pct, irq_pm, nmi_pm, r, rel, low_left, nrst, rst_pm_div; reg dump, pre_done; integer nmi_chg;
    reg [1023:0] dir; reg [8*256-1:0] fname;

    always @(posedge clk) if (res_n && rw === 1'b0) mem[a] <= d_out;

    initial begin
        if (!$value$plusargs("dir=%s", dir)) dir = "build/c8";
        if (!$value$plusargs("nprog=%d", nprog)) nprog = 1;
        if (!$value$plusargs("nst=%d", nst)) nst = 1000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("rdy=%d", rdy_pct)) rdy_pct = 10;
        if (!$value$plusargs("irq=%d", irq_pm)) irq_pm = 30;
        if (!$value$plusargs("nmi=%d", nmi_pm)) nmi_pm = 10;
        if (!$value$plusargs("rstdiv=%d", rst_pm_div)) rst_pm_div = 1500;   // 1 in N cycles starts a reset
        r = $urandom(seed);
        for (p = 0; p < nprog; p = p + 1) begin
            $sformat(fname, "%0s/prog%0d/mem.hex", dir, p);
            $readmemh(fname, mem);
            $sformat(fname, "%0s/prog%0d/pins.txt", dir, p);
            fd = $fopen(fname, "w");
            res_n = 0; rdy = 1; irq_n = 1; nmi_n = 1; rel = 10; nrst = 0; dump = 0; low_left = 0; pre_done = 0; nmi_chg = -10;
            for (n = 0; n < nst; n = n + 1) begin
                @(negedge clk);                       // inputs for this cycle (the edge that started it has passed)
                if (n == 10) begin res_n = 1; rel = 10; end
                if (res_n && n >= 40 && n >= rel + 10 && ($urandom % rst_pm_div) == 0) begin   // mid-run reset
                    res_n = 0; low_left = 8 + ($urandom % 5); irq_n = 1; nmi_n = 1; dump = 1; pre_done = 0;
                end else if (!res_n && n > 10) begin
                    low_left = low_left - 1;
                    if (low_left == 0) begin res_n = 1; rel = n; end
                end
                if (!res_n) rdy = 1;
                if (n >= 10 && res_n) begin
                    // spec §5 (#40): rdy = 1 until the edge that starts reset cycle 8 (rel + 8); random from there
                    rdy = (n < rel + 8) ? 1'b1 : (($urandom % 100) >= rdy_pct);
                    #1;                               // let sync settle after any input change
                    if (sync === 1'b1 && a == 16'h0200) pre_done = 1;   // the preamble has jumped to the stream
                    if (sync === 1'b1 && pre_done) begin   // §5: the preamble sets S before an interrupt can push
                        if (($urandom % 1000) < irq_pm) irq_n = ~irq_n;
                        // §6 / p.38: nmi_n stays low >= 2 cycles; RDY-held fetches give consecutive sync cycles, so
                        // a change is allowed only 2+ cycles after the previous one
                        if (($urandom % 1000) < nmi_pm && n >= nmi_chg + 2) begin nmi_n = ~nmi_n; nmi_chg = n; end
                    end
                end
                #1;
                $fdisplay(fd, "%h %b %b %b %h %b %b %b %b", a, rw, sync, d_oe, d_out, rdy, irq_n, nmi_n, res_n);
                if (dump) begin                           // RAM after the edge ending this (first res_n = 0) cycle
                    @(posedge clk); #1;
                    $sformat(fname, "%0s/prog%0d/mem_rst%0d.hex", dir, p, nrst);
                    $writememh(fname, mem);
                    nrst = nrst + 1; dump = 0;
                end
            end
            $fclose(fd);
            @(posedge clk); #1;                       // the last logged cycle completes (its write, if any, lands)
            $sformat(fname, "%0s/prog%0d/mem_end.hex", dir, p); $writememh(fname, mem);
        end
        $display("DONE c8 resets tb");
        $finish;
    end
endmodule
