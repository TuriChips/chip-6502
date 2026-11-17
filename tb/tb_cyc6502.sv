// Cycle-by-cycle testbench on the m6502 pins (spec 2, 4.0): the memory image (RAM below 8000, ROM above: writes are put on the bus but not stored, as in the model) comes
// from -DMEMFILE, the expected cycles from +EXP (lines `AAAA R S DD`, one per clock from the first SYNC after reset; DD = the byte written, xx for reads). Compared every clock:
// a, rw, sync, d_oe (= NOT rw) and d_out when writing; no X/Z on any output. IRQ, NMI and SO are held inactive; RDY is driven from a fifth column (C3). +N=<lines>.
`timescale 1ns/1ps
module tb_cyc6502;
  reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1, so_n = 1;
  wire [15:0] a; wire [7:0] d_out; wire d_oe, rw, sync; wire [7:0] d_in;
  reg [7:0] mem [0:65535];
  m6502 dut (.clk(clk), .res_n(res_n), .a(a), .d_in(d_in), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n));
  assign d_in = mem[a];
  always #5 clk = ~clk;
  reg [15:0] ea [0:131071]; reg er [0:131071]; reg es [0:131071]; reg erdy [0:131071]; reg eirq [0:131071]; reg enmi [0:131071]; reg [7:0] ed [0:131071];
  integer n = 0, idx = 0, errors = 0, i, fd, r, cyc = 0; reg started = 0; string expf;
  reg [15:0] xa; reg [7:0] xd; integer xr, xs, xrdy, xirq, xnmi;
  initial begin
    for (i = 0; i < 65536; i = i + 1) mem[i] = 8'h00;
    $readmemh(`MEMFILE, mem);
    if (!$value$plusargs("EXP=%s", expf)) begin $display("FAIL no +EXP"); $finish; end
    if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL empty or missing +N"); $finish; end
    fd = $fopen(expf, "r");
    for (i = 0; i < n; i = i + 1) begin r = $fscanf(fd, "%h %d %d %s %d %d %d\n", xa, xr, xs, expf_d, xrdy, xirq, xnmi); ea[i] = xa; er[i] = xr; es[i] = xs; erdy[i] = xrdy; eirq[i] = xirq; enmi[i] = xnmi; ed[i] = (expf_d == "xx") ? 8'h00 : hex2(expf_d); end
    if (!$value$plusargs("RESET_AT=%d", rst_at)) rst_at = -1;
    if (!$value$plusargs("RESET_LEN=%d", rst_len)) rst_len = 10;
    if (!$value$plusargs("SYNC_CYCLE=%d", sync_cycle)) sync_cycle = 8;
    if (!$value$plusargs("VEC_CYCLE=%d", vec_cycle)) vec_cycle = 6;
    repeat (12) @(posedge clk); @(negedge clk); res_n = 1; rcyc = 0;       // RESET held low for >= 8 cycles (spec 5)
  end
  string expf_d;
  function [7:0] hex2(input string s); hex2 = 0; hex2 = (s[0] >= "A" ? s[0] - "A" + 10 : s[0] - "0") * 16 + (s[1] >= "A" ? s[1] - "A" + 10 : s[1] - "0"); endfunction
  // RDY: the value for the clock that starts at this edge (changes only at cycle starts, spec 7)
  always @(posedge clk) if (res_n && started && idx < n) begin rdy <= erdy[idx]; irq_n <= eirq[idx]; nmi_n <= enmi[idx]; end   // IRQ/NMI: changed only at the edge that starts an instruction fetch (spec 6, 7), as generated
  // C6: +RESET_AT=<cycle index> asserts res_n low from the clock that starts there for +RESET_LEN clocks (default 10, >= 8: spec 5); the expected rows resume with the
  // restarted run. Compared (spec 5, chip-6502#29): while res_n = 0 (from the 2nd clock) and in reset cycles 1-7 after release: rw = 1, d_oe = 0; cycles 6-7: a = FFFC, FFFD;
  // the first SYNC must be cycle 8. Cycle 1 is the cycle that starts at the first edge where res_n is sampled 1.
  integer rst_at = -1, rst_len = 10, rlow = 0, rcyc = 0, sync_cycle = 8, vec_cycle = 6; reg rdone = 0;   // +SYNC_CYCLE / +VEC_CYCLE: diagnostics only (the spec says 8 and 6)
  reg seen_hi = 0;      // res_n was sampled 1 at a rising edge since the last reset: reset cycle 1 is the cycle that starts at that edge (spec 5, #30; Igris's ruling on #37)
  always @(posedge clk) begin
    if (res_n === 1'b1) seen_hi <= 1;
    if (rst_at >= 0 && !rdone && started && res_n && idx == rst_at) begin res_n <= 0; rlow <= 1; rdone <= 1; started <= 0; seen_hi <= 0; end
    else if (!res_n && rlow > 0) begin
      rlow <= rlow + 1; if (rlow + 1 > rst_len) begin res_n <= 1; rlow <= 0; rcyc <= 0; end
    end
  end
  always @(negedge clk) begin
    cyc = cyc + 1;
    if (!res_n) begin
      if (rlow >= 2 || (rst_at < 0 && cyc > 2)) if (rw !== 1'b1 || d_oe !== 1'b0) begin errors = errors + 1; if (errors < 10) $display("FAIL while res_n = 0: rw=%b d_oe=%b", rw, d_oe); end
    end else if (!started && seen_hi) begin
      rcyc = rcyc + 1;
      if (rcyc < sync_cycle && (rw !== 1'b1 || d_oe !== 1'b0)) begin errors = errors + 1; if (errors < 10) $display("FAIL reset cycle %0d: rw=%b d_oe=%b (reads only)", rcyc, rw, d_oe); end
      if (rcyc == vec_cycle && a !== 16'hFFFC) begin errors = errors + 1; if (errors < 10) $display("FAIL reset cycle 6: a=%h, expected FFFC", a); end
      if (rcyc == vec_cycle + 1 && a !== 16'hFFFD) begin errors = errors + 1; if (errors < 10) $display("FAIL reset cycle 7: a=%h, expected FFFD", a); end
      if (sync === 1'b1) begin
        if (rcyc != sync_cycle) begin errors = errors + 1; if (errors < 10) $display("FAIL the first SYNC is reset cycle %0d, expected 8", rcyc); end
        started = 1;
      end
    end
    if (res_n && started) begin
      if (^{a, d_out, d_oe, rw, sync} === 1'bx && !(rw === 1'b1 && ^{a, d_oe, rw, sync} !== 1'bx)) begin errors = errors + 1; if (errors < 10) $display("FAIL C7 X/Z on an output at cycle %0d", idx); end
      if (a !== ea[idx] || rw !== er[idx] || sync !== es[idx] || d_oe !== !er[idx] || (!er[idx] && d_out !== ed[idx])) begin
        errors = errors + 1;
        if (errors < 10) $display("FAIL cycle %0d: expected a=%h rw=%b sync=%b d=%h (write data, if rw=0), got a=%h rw=%b sync=%b d_oe=%b d_out=%h", idx, ea[idx], er[idx], es[idx], ed[idx], a, rw, sync, d_oe, d_out);
      end
      if (rw === 1'b0 && a < 16'h8000) mem[a] = d_out;             // RAM write (ROM above 8000 ignores writes)
      idx = idx + 1;
      if (idx == n) begin $display("%s: cycles=%0d errors=%0d", errors ? "FAIL" : "PASS", n, errors); $finish; end
    end
    if (cyc > 3 * n + 400) begin $display("FAIL timeout after %0d cycles (idx %0d)", cyc, idx); $finish; end
  end
endmodule
