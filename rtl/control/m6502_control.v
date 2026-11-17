// m6502_control: IR, the per-instruction cycle plan, interrupt and reset sequences, TMP (spec 4, 4.1, 5, 6).
// Ports and codes: docs/blocks.md sections 2 and 3 (chip-6502#9). Added by this block (chip-6502 PR text):
//   tmp            the TMP latch: RMW read, and the branch offset
//   regs_din_tmp   1 = give m6502_regs TMP as its d_in (branch T2: PCL <- PCL + offset, chip-6502#21 Decision)
//   alu_op 22      SEV (V <- 1), for the S.O. pin; not in Ada's table yet
//   p_i            the I flag (ALU p_push bit 2)
// The cycle plan is the table m6502_plan.v (generated, checked against the spec's cycle counts); the opcode decode is
// m6502_decode.v. Every strobe is masked by `go`: a read held by RDY changes nothing.
module m6502_control (
    input  wire        clk,
    input  wire        res_n,
    input  wire [2:0]  t,
    input  wire        go,
    input  wire [3:0]  rs,
    input  wire [7:0]  d_in,
    input  wire [3:0]  flags,          // {N, V, Z, C}
    input  wire        p_i,
    input  wire        ab_carry,
    input  wire [7:0]  pcl,            // PC[7:0]
    input  wire        irq_n,
    input  wire        nmi_n,
    input  wire        so_n,
    output wire        rw,
    output wire        d_oe,
    output wire        sync,
    output wire        cyc_rd,
    output wire        cyc_last,
    output reg  [2:0]  addr_sel,
    output reg  [2:0]  vec_sel,
    output reg  [3:0]  ab_op,
    output reg  [1:0]  pc_op,
    output reg  [1:0]  s_op,
    output reg  [4:0]  alu_op,
    output reg  [1:0]  alu_a_sel,
    output reg  [2:0]  alu_b_sel,
    output reg         a_we,
    output reg         f_we,
    output reg         pull_p,
    output wire        push_b,
    output reg         x_we,
    output reg         y_we,
    output reg  [2:0]  d_out_sel,
    output wire        regs_din_tmp,
    output wire [7:0]  tmp
);
    localparam [4:0] M_IMP = 0, M_REL = 10, M_PLX = 12, M_BRK = 16;
    localparam [4:0] OP_SEI = 18, OP_SEV = 22;

    reg [7:0] ir, tmp_r;
    reg       intseq, intnmi, nmi_latch, nmi_q, nmi_det_q, so_q, so_latch, br3;
    reg [1:0] s1, s2, s3;              // poll samples {irq, nmi} at the end of the last 3 completed cycles (spec 6 poll rule)
    assign tmp = tmp_r;

    wire running = (rs == 4'd8);

    // ---- decode and plan
    // verilator lint_off UNUSEDSIGNAL
    wire        d_ok;
    wire [4:0]  mode, aop;
    wire [1:0]  cls, asel, src;
    wire [2:0]  bsel;
    wire        awe, fwe, xwe, ywe;
    m6502_decode u_dec (.ir(ir), .ok(d_ok), .mode(mode), .cls(cls), .aop(aop), .asel(asel), .bsel(bsel),
                        .awe(awe), .fwe(fwe), .xwe(xwe), .ywe(ywe), .src(src));

    reg flag_v;
    always @(*) begin
        case (ir[7:6])
            2'b00:   flag_v = flags[3];   // N
            2'b01:   flag_v = flags[2];   // V
            2'b10:   flag_v = flags[0];   // C
            default: flag_v = flags[1];   // Z
        endcase
    end
    wire       taken   = (flag_v == ir[5]);
    wire [8:0] br_sum  = {1'b0, pcl} + {1'b0, tmp_r};   // only the carry out is used
    wire       crossed = br_sum[8] ^ tmp_r[7];
    // verilator lint_on UNUSEDSIGNAL

    wire [2:0] p_addr, p_vec, p_dout; wire [3:0] p_ab; wire [1:0] p_pc, p_s;
    wire p_wr, p_last, p_ex, p_tmpl, p_tmpb, p_dint, p_pull, p_pushb, p_dsrc, p_sei;
    m6502_plan u_plan (.mode(mode), .cls(cls), .t(t), .car(ab_carry), .tk(taken), .cr(crossed), .isq(intseq), .nmi(intnmi),
                       .addr(p_addr), .vec(p_vec), .ab(p_ab), .pc(p_pc), .s(p_s), .dout(p_dout), .wr(p_wr), .last(p_last),
                       .ex(p_ex), .tmpl(p_tmpl), .tmpb(p_tmpb), .dint(p_dint), .pull(p_pull), .pushb(p_pushb), .dsrc(p_dsrc),
                       .sei(p_sei));

    // interrupt decision at T0 from the poll sample of the second-to-last cycle of the previous instruction (spec 6 poll
    // rule, chip-6502#25): s2 normally; s3 after a taken branch with no page cross (it polls at the end of its cycle 1)
    wire [1:0] poll_s  = br3 ? s3 : s2;
    wire       int_nmi = poll_s[0];
    wire       int_now = poll_s[0] | poll_s[1];
    wire t0      = running & (t == 3'd0);
    wire body    = running & (t != 3'd0);

    wire wr_cyc  = body & p_wr;
    assign rw     = ~wr_cyc;
    assign d_oe   = wr_cyc;
    assign cyc_rd = rw;
    assign sync   = t0;
    assign cyc_last = body & p_last;
    assign push_b = body & p_pushb;
    assign regs_din_tmp = body & p_dint;

    always @(*) begin
        addr_sel = 3'd0; vec_sel = 3'd0; ab_op = 4'd0; pc_op = 2'd0; s_op = 2'd0; alu_op = 5'd0; alu_a_sel = 2'd0;
        alu_b_sel = 3'd0; a_we = 1'b0; f_we = 1'b0; pull_p = 1'b0; x_we = 1'b0; y_we = 1'b0; d_out_sel = 3'd0;
        if (!running) begin
            // reset sequence (spec 4, 5): reads only; FFFC/FFFD load PC
            case (rs)
                4'd3, 4'd4, 4'd5: begin addr_sel = 3'd3; s_op = 2'd1; end    // {01,S}, {01,S-1}, {01,S-2}: reads, S steps down as pushes would
                4'd6: begin addr_sel = 3'd5; vec_sel = 3'd2; ab_op = 4'd1; end
                4'd7: begin addr_sel = 3'd5; vec_sel = 3'd3; ab_op = 4'd7; end
                default: ;
            endcase
        end else if (t0) begin
            pc_op = int_now ? 2'd0 : 2'd1;              // a forced BRK doesn't advance PC
            if (so_latch) begin alu_op = OP_SEV; f_we = 1'b1; end
        end else begin
            addr_sel = p_addr; vec_sel = p_vec; ab_op = p_ab; pc_op = p_pc; s_op = p_s;
            d_out_sel = p_dsrc ? {1'b0, src} : p_dout;
            if (p_ex) begin
                alu_op = aop; alu_a_sel = asel; a_we = awe; f_we = fwe; x_we = xwe; y_we = ywe;
                alu_b_sel = p_tmpb ? 3'd1 : ((mode == M_IMP) ? bsel : 3'd0);
            end
            if (p_pull && !(mode == M_PLX && awe)) pull_p = 1'b1;          // PLP, RTI (not PLA)
            if (p_sei) begin alu_op = OP_SEI; f_we = 1'b1; end
            if (mode == M_IMP && ir == 8'h9A && p_last) s_op = 2'd3;      // TXS
        end
        // an RDY-held cycle changes nothing
        if (!go) begin
            ab_op = 4'd0; pc_op = 2'd0; s_op = 2'd0; a_we = 1'b0; f_we = 1'b0; pull_p = 1'b0; x_we = 1'b0; y_we = 1'b0;
            alu_op = 5'd0;
        end
    end

    // ---- state
    wire nmi_det = nmi_q & ~nmi_n;                               // falling edge seen at this clock edge
    wire sample_irq = ~irq_n & ~p_i;                             // irq_n at the poll edge, I as it stands in that cycle
    always @(posedge clk) begin
        if (!res_n) begin
            ir <= 8'd0; tmp_r <= 8'd0; intseq <= 1'b0; intnmi <= 1'b0;
            nmi_latch <= 1'b0; nmi_q <= 1'b1; nmi_det_q <= 1'b0; so_q <= 1'b1; so_latch <= 1'b0;
            br3 <= 1'b0; s1 <= 2'd0; s2 <= 2'd0; s3 <= 2'd0;
        end else begin
            nmi_q <= nmi_n; so_q <= so_n; nmi_det_q <= nmi_det;
            // NMI: pending from the edge it is detected; a poll sees it from the next edge on (it samples the register)
            if (nmi_det) nmi_latch <= 1'b1;
            if (so_q & ~so_n) so_latch <= 1'b1;
            if (!running) begin
                s1 <= 2'd0; s2 <= 2'd0; s3 <= 2'd0; br3 <= 1'b0;   // the reset sequence doesn't poll
            end else if (go) begin
                if (t == 3'd0) begin
                    so_latch <= so_q & ~so_n;
                    br3 <= 1'b0;
                    if (int_now) begin
                        ir <= 8'h00; intseq <= 1'b1; intnmi <= int_nmi;
                        // committing to the NMI sequence clears pending, except for edges detected after the poll edge
                        if (int_nmi) nmi_latch <= nmi_det_q | nmi_det;
                    end else begin
                        ir <= d_in; intseq <= 1'b0; intnmi <= 1'b0;
                    end
                    // sequences don't poll: a forced BRK and a real BRK clear the samples
                    if (int_now || d_in == 8'h00) begin s1 <= 2'd0; s2 <= 2'd0; s3 <= 2'd0; end
                    else begin s3 <= s2; s2 <= s1; s1 <= {sample_irq, nmi_latch}; end
                end else begin
                    if (p_tmpl) tmp_r <= d_in;
                    if (mode == M_BRK) begin s1 <= 2'd0; s2 <= 2'd0; s3 <= 2'd0; end
                    else begin s3 <= s2; s2 <= s1; s1 <= {sample_irq, nmi_latch}; end
                    // a taken branch with no page cross ends after cycle 3 but polled at the end of cycle 1
                    if (mode == M_REL && t == 3'd2 && p_last) br3 <= 1'b1;
                end
            end
        end
    end
endmodule
