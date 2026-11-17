// m6502: CPU top level. Pins per spec section 2, in that order. Wiring and the data muxes of blocks.md section 2.
// verilator lint_off DECLFILENAME
module m6502 (
    input  wire        clk,
    input  wire        res_n,
    output wire [15:0] a,
    input  wire [7:0]  d_in,
    output wire [7:0]  d_out,
    output wire        d_oe,
    output wire        rw,
    output wire        sync,
    input  wire        rdy,
    input  wire        irq_n,
    input  wire        nmi_n,
    input  wire        so_n
);
    wire        reset = ~res_n;                      // datapath reset, active high
    wire [2:0]  t;     wire go;  wire [3:0] rs;
    wire        cyc_rd, cyc_last;
    wire [2:0]  addr_sel, vec_sel, alu_b_sel, d_out_sel;
    wire [3:0]  ab_op;
    wire [1:0]  pc_op, s_op, alu_a_sel;
    wire [4:0]  alu_op;
    wire        a_we, f_we, pull_p, push_b, x_we, y_we, regs_din_tmp;
    wire [7:0]  tmp, a_out, p_push, result, x_out, y_out, s_out;
    wire [3:0]  flags;
    wire [15:0] pc;
    wire        ab_carry;

    m6502_timing u_timing (.clk(clk), .res_n(res_n), .rdy(rdy), .cyc_rd(cyc_rd), .cyc_last(cyc_last),
                           .t(t), .go(go), .rs(rs));

    m6502_control u_control (
        .clk(clk), .res_n(res_n), .t(t), .go(go), .rs(rs), .d_in(d_in), .flags(flags), .p_i(p_push[2]),
        .ab_carry(ab_carry), .pcl(pc[7:0]), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n),
        .rw(rw), .d_oe(d_oe), .sync(sync), .cyc_rd(cyc_rd), .cyc_last(cyc_last),
        .addr_sel(addr_sel), .vec_sel(vec_sel), .ab_op(ab_op), .pc_op(pc_op), .s_op(s_op),
        .alu_op(alu_op), .alu_a_sel(alu_a_sel), .alu_b_sel(alu_b_sel), .a_we(a_we), .f_we(f_we),
        .pull_p(pull_p), .push_b(push_b), .x_we(x_we), .y_we(y_we), .d_out_sel(d_out_sel),
        .regs_din_tmp(regs_din_tmp), .tmp(tmp)
    );

    // ALU operands (blocks.md section 2): a_in 0 A, 1 X, 2 Y; b 0 d_in, 1 TMP, 2 X, 3 Y, 4 S, 5 A
    wire [7:0] alu_a_in = (alu_a_sel == 2'd1) ? x_out : (alu_a_sel == 2'd2) ? y_out : a_out;
    wire [7:0] alu_b = (alu_b_sel == 3'd1) ? tmp : (alu_b_sel == 3'd2) ? x_out : (alu_b_sel == 3'd3) ? y_out :
                       (alu_b_sel == 3'd4) ? s_out : (alu_b_sel == 3'd5) ? a_out : d_in;

    m6502_alu u_alu (
        .clk(clk), .reset(reset), .op(alu_op), .a_in(alu_a_in), .b(alu_b), .a_we(a_we), .f_we(f_we),
        .pull_p(pull_p), .push_b(push_b), .a_out(a_out), .p_push(p_push), .flags(flags), .result(result)
    );

    m6502_regs u_regs (
        .clk(clk), .reset(reset), .d_in(regs_din_tmp ? tmp : d_in), .wdata(result), .x_we(x_we), .y_we(y_we),
        .ab_op(ab_op), .pc_op(pc_op), .s_op(s_op), .addr_sel(addr_sel), .vec_sel(vec_sel),
        .addr(a), .ab_carry(ab_carry), .x_out(x_out), .y_out(y_out), .s_out(s_out), .pc(pc)
    );

    // d_out (blocks.md section 2): 0 A, 1 X, 2 Y, 3 P as pushed, 4 PCH, 5 PCL, 6 TMP, 7 ALU result
    assign d_out = (d_out_sel == 3'd0) ? a_out : (d_out_sel == 3'd1) ? x_out : (d_out_sel == 3'd2) ? y_out :
                   (d_out_sel == 3'd3) ? p_push : (d_out_sel == 3'd4) ? pc[15:8] : (d_out_sel == 3'd5) ? pc[7:0] :
                   (d_out_sel == 3'd6) ? tmp : result;
endmodule
