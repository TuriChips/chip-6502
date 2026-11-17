// Cycle-by-cycle testbench on the m6502 pins (spec 2, 4.0): the memory image (RAM below 8000, ROM above: writes are put on the bus but not stored, as in the model) comes
// from -DMEMFILE, the expected cycles from +EXP (lines `AAAA R S DD`, one per clock from the first SYNC after reset; DD = the byte written, xx for reads). Compared every clock:
// a, rw, sync, d_oe (= NOT rw) and d_out when writing; no X/Z on any output. RDY, IRQ, NMI and SO are held inactive. +N=<lines>.
`timescale 1ns/1ps
module tb_cyc6502;
  reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1, so_n = 1;
  wire [15:0] a; wire [7:0] d_out; wire d_oe, rw, sync; wire [7:0] d_in;
  reg [7:0] mem [0:65535];
  m6502 dut (.clk(clk), .res_n(res_n), .a(a), .d_in(d_in), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n));
  assign d_in = mem[a];
  always #5 clk = ~clk;
  reg [15:0] ea [0:131071]; reg er [0:131071]; reg es [0:131071]; reg [7:0] ed [0:131071];
  integer n = 0, idx = 0, errors = 0, i, fd, r, cyc = 0; reg started = 0; string expf;
  reg [15:0] xa; reg [7:0] xd; integer xr, xs;
  initial begin
    for (i = 0; i < 65536; i = i + 1) mem[i] = 8'h00;
    $readmemh(`MEMFILE, mem);
    if (!$value$plusargs("EXP=%s", expf)) begin $display("FAIL no +EXP"); $finish; end
    if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL empty or missing +N"); $finish; end
    fd = $fopen(expf, "r");
    for (i = 0; i < n; i = i + 1) begin r = $fscanf(fd, "%h %d %d %s\n", xa, xr, xs, expf_d); ea[i] = xa; er[i] = xr; es[i] = xs; ed[i] = (expf_d == "xx") ? 8'h00 : hex2(expf_d); end
    repeat (12) @(posedge clk); @(negedge clk); res_n = 1;       // RESET held low for >= 8 cycles (spec 5)
  end
  string expf_d;
  function [7:0] hex2(input string s); hex2 = 0; hex2 = (s[0] >= "A" ? s[0] - "A" + 10 : s[0] - "0") * 16 + (s[1] >= "A" ? s[1] - "A" + 10 : s[1] - "0"); endfunction
  always @(negedge clk) if (res_n) begin
    cyc = cyc + 1;
    if (!started && sync === 1'b1) started = 1;                    // comparison starts at the first SYNC after reset (spec 5)
    if (started) begin
      if (^{a, d_out, d_oe, rw, sync} === 1'bx && !(rw === 1'b1 && ^{a, d_oe, rw, sync} !== 1'bx)) begin errors = errors + 1; if (errors < 10) $display("FAIL C7 X/Z on an output at cycle %0d", idx); end
      if (a !== ea[idx] || rw !== er[idx] || sync !== es[idx] || d_oe !== !er[idx] || (!er[idx] && d_out !== ed[idx])) begin
        errors = errors + 1;
        if (errors < 10) $display("FAIL cycle %0d: expected a=%h rw=%b sync=%b%s, got a=%h rw=%b sync=%b d_oe=%b d_out=%h", idx, ea[idx], er[idx], es[idx], er[idx] ? "" : $sformatf(" d=%h", ed[idx]), a, rw, sync, d_oe, d_out);
      end
      if (rw === 1'b0 && a < 16'h8000) mem[a] = d_out;             // RAM write (ROM above 8000 ignores writes)
      idx = idx + 1;
      if (idx == n) begin $display("%s: cycles=%0d errors=%0d", errors ? "FAIL" : "PASS", n, errors); $finish; end
    end
    if (cyc > 3 * n + 200) begin $display("FAIL timeout after %0d cycles (idx %0d)", cyc, idx); $finish; end
  end
endmodule
