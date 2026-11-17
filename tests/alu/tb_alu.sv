// Block-level check of m6502_alu against the vectors of tests/alu/gen_vectors.py (expected values from the model written from the spec).
// Per vector: reset, optional SED / SEC, LD a, then the op; `result` is sampled before the closing edge (combinational), a_out and p_push after it.
// Plusargs: +VEC=<hex file> +N=<vectors>. Defines: none. Block ports as in docs/blocks.md section 3 (PR #9 / #16).
`timescale 1ns/1ps
module tb_alu;
  reg clk = 0, reset = 0; reg [4:0] op = 0; reg [7:0] a_in = 0, b = 0; reg a_we = 0, f_we = 0, pull_p = 0, push_b = 0;
  wire [7:0] a_out, p_push, result; wire [3:0] flags;
  m6502_alu dut (.clk(clk), .reset(reset), .op(op), .a_in(a_in), .b(b), .a_we(a_we), .f_we(f_we), .pull_p(pull_p), .push_b(push_b),
                 .a_out(a_out), .p_push(p_push), .flags(flags), .result(result));
  reg [47:0] mem [0:2100000]; integer n, i, bad = 0, badop [0:31], k; string vf;
  reg [47:0] w0, w1; reg [4:0] vop; reg [7:0] va, vb, e_res, e_a, e_p; reg vc, vd, vpb, chk_res, chk_a; reg [7:0] r_res;
  task tick; begin #5 clk = 1; #5 clk = 0; end endtask
  initial begin
    if (!$value$plusargs("VEC=%s", vf)) begin $display("FAIL no +VEC"); $finish; end
    if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL no +N"); $finish; end
    for (k = 0; k < 32; k = k + 1) badop[k] = 0;
    $readmemh(vf, mem);
    for (i = 0; i < n; i = i + 1) begin
      w0 = mem[2*i]; w1 = mem[2*i+1];
      chk_res = w0[47]; chk_a = w0[46]; vop = w0[45:41]; va = w0[40:33]; vb = w0[32:25]; vc = w0[24]; vd = w0[23]; vpb = w0[22];
      e_res = w1[23:16]; e_a = w1[15:8]; e_p = w1[7:0];
      reset = 1; a_we = 0; f_we = 0; op = 0; tick; reset = 0;
      if (vd) begin op = 5'd20; f_we = 1; tick; end                  // SED
      if (vc) begin op = 5'd16; f_we = 1; tick; end                  // SEC
      op = 5'd14; b = va; a_in = 8'h00; a_we = 1; f_we = 0; tick;    // LD A <- a (flags unchanged)
      op = vop; a_in = va; b = vb; push_b = vpb; f_we = 1; a_we = chk_a; #1; r_res = result; #4; clk = 1; #5 clk = 0; #1;
      if ((chk_res && r_res !== e_res) || (chk_a && a_out !== e_a) || p_push !== e_p || (!chk_a && a_out !== va)) begin
        bad = bad + 1; badop[vop] = badop[vop] + 1;
        if (bad <= 10) $display("MISMATCH op %0d a=%h b=%h c=%b d=%b: result %h (exp %h%s) a_out %h (exp %h) P %h (exp %h)", vop, va, vb, vc, vd, r_res, e_res, chk_res ? "" : " unchecked", a_out, chk_a ? e_a : va, p_push, e_p);
      end
    end
    for (k = 0; k < 32; k = k + 1) if (badop[k]) $display("op %0d: %0d mismatches", k, badop[k]);
    $display("%s: %0d vectors, %0d mismatches", bad ? "FAIL" : "PASS", n, bad);
    $finish;
  end
endmodule
