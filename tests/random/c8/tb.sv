// C8 testbench (Beru, chip-6502#6): runs random programs on the RTL m6502 and dumps every cycle's pins
// and inputs; tests/random/c8/run.py replays the inputs through ref/pins6502.py and compares.
// Memory is the testbench's own 64 KiB array (combinational read, write at the clock edge when rw = 0).
// Stimulus (spec §6, §2): rdy random in any cycle; irq_n / nmi_n change only in a cycle with sync = 1
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

    integer fd, p, n, nprog, nst, seed, rdy_pct, irq_pm, nmi_pm, r;
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
        r = $urandom(seed);
        for (p = 0; p < nprog; p = p + 1) begin
            $sformat(fname, "%0s/prog%0d/mem.hex", dir, p);
            $readmemh(fname, mem);
            $sformat(fname, "%0s/prog%0d/pins.txt", dir, p);
            fd = $fopen(fname, "w");
            res_n = 0; rdy = 1; irq_n = 1; nmi_n = 1;
            for (n = 0; n < nst; n = n + 1) begin
                @(negedge clk);                       // inputs for this cycle (the edge that started it has passed)
                if (n == 10) res_n = 1;
                if (n >= 10) begin
                    rdy = ($urandom % 100) >= rdy_pct;
                    #1;                               // let sync settle after any input change
                    if (sync === 1'b1 && n >= 30) begin
                        if (($urandom % 1000) < irq_pm) irq_n = ~irq_n;
                        if (($urandom % 1000) < nmi_pm) nmi_n = ~nmi_n;
                    end
                end
                #1;
                $fdisplay(fd, "%h %b %b %b %h %b %b %b %b", a, rw, sync, d_oe, d_out, rdy, irq_n, nmi_n, res_n);
            end
            $fclose(fd);
        end
        $display("DONE c8 tb");
        $finish;
    end
endmodule
