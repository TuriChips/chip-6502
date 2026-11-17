// Directed C8 (Beru, chip-6502#6): replays a fixed per-cycle stimulus on the RTL m6502 and dumps the same pins.txt as
// tb.sv, so run.compare() judges it against the model. <dir>/mem.hex = memory, <dir>/stim.txt = one line per cycle
// "rdy irq_n nmi_n res_n" (binary digits), <dir>/pins.txt = output. Driven by tests/random/c8/directed.py.
`timescale 1ns/1ps
module tb;
    reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1;
    reg [7:0] mem [0:65535];
    reg [3:0] stim [0:65535];
    wire [15:0] a; wire [7:0] d_out; wire d_oe, rw, sync;
    m6502 dut(.clk(clk), .res_n(res_n), .a(a), .d_in(mem[a]), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync),
              .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(1'b1));
    always #5 clk = ~clk;
    always @(posedge clk) if (res_n && rw === 1'b0) mem[a] <= d_out;
    integer fd, n, nst; reg [1023:0] dir; reg [8*256-1:0] fname;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) dir = "build/directed";
        if (!$value$plusargs("nst=%d", nst)) nst = 100;
        $sformat(fname, "%0s/mem.hex", dir); $readmemh(fname, mem);
        $sformat(fname, "%0s/stim.txt", dir); $readmemb(fname, stim);
        $sformat(fname, "%0s/pins.txt", dir); fd = $fopen(fname, "w");
        for (n = 0; n < nst; n = n + 1) begin
            @(negedge clk);
            {rdy, irq_n, nmi_n, res_n} = stim[n];
            #2 $fdisplay(fd, "%h %b %b %b %h %b %b %b %b", a, rw, sync, d_oe, d_out, rdy, irq_n, nmi_n, res_n);
        end
        $fclose(fd); $display("DONE directed tb"); $finish;
    end
endmodule
