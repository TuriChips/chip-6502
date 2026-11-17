// Positive bus_conflict check (spec §8 C7; Beru, chip-6502#6): m6502_system with a C8 program, dumping
// a rw d_oe bus_conflict per cycle to <dir>/conflict.txt. Driven by conflict_check.py.
`timescale 1ns/1ps
module tb;
    reg clk = 0, res_n = 0;
    wire [15:0] a; wire [7:0] d_out, bus, con_data; wire d_oe, rw, sync, con_strobe, bus_conflict;
    m6502_system sys(.clk(clk), .res_n(res_n), .rdy(1'b1), .irq_n(1'b1), .nmi_n(1'b1), .so_n(1'b1),
        .a(a), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .bus(bus), .con_data(con_data),
        .con_strobe(con_strobe), .bus_conflict(bus_conflict));
    always #5 clk = ~clk;
    integer fd, n, nst; reg [1023:0] dir; reg [8*256-1:0] fname;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) dir = "build/conflict";
        if (!$value$plusargs("nst=%d", nst)) nst = 2000;
        $sformat(fname, "%0s/mem.hex", dir); $readmemh(fname, sys.mem.mem);
        $sformat(fname, "%0s/conflict.txt", dir); fd = $fopen(fname, "w");
        for (n = 0; n < nst; n = n + 1) begin
            @(negedge clk); if (n == 10) res_n = 1;
            #1 $fdisplay(fd, "%h %b %b %b", a, rw, d_oe, bus_conflict);
        end
        $fclose(fd); $display("DONE conflict tb"); $finish;
    end
endmodule
