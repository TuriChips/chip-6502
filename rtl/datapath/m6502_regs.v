// Ada: 6502 X, Y, S, PC and the address latches (ADL, ADH, PL). Ports and codes: docs/blocks.md sections 2 and 3 (chip-6502#9).
// ab_op, pc_op and s_op are independent fields. If ab_op 7..10 writes PC, pc_op is ignored (ab_op wins).
module m6502_regs (
    input  wire        clk,
    input  wire        reset,
    input  wire [7:0]  d_in,
    input  wire [7:0]  wdata,
    input  wire        x_we,
    input  wire        y_we,
    input  wire [3:0]  ab_op,
    input  wire [1:0]  pc_op,
    input  wire [1:0]  s_op,
    input  wire [2:0]  addr_sel,
    input  wire [2:0]  vec_sel,
    output reg  [15:0] addr,
    output wire        ab_carry,
    output wire [7:0]  x_out,
    output wire [7:0]  y_out,
    output wire [7:0]  s_out,
    output wire [15:0] pc
);
    reg [7:0]  x, y, s;
    reg [15:0] r_pc;
    reg [7:0]  adl, adh, pl;
    reg        carry_q, br_sign;

    assign ab_carry = carry_q;
    assign x_out = x;
    assign y_out = y;
    assign s_out = s;
    assign pc    = r_pc;

    // ---- address pins (combinational)
    wire [7:0] vec_lo = 8'hFA + {5'd0, vec_sel};
    always @* begin
        case (addr_sel)
            3'd0: addr = r_pc;
            3'd1: addr = {adh, adl};
            3'd2: addr = {8'h00, adl};
            3'd3: addr = {8'h01, s};
            3'd4: addr = {adh, adl};        // ADH is never carried by ab_op 3/4/14/15, so this is the uncarried address
            3'd5: addr = {8'hFF, vec_lo};
            default: addr = 16'h0000;
        endcase
    end

    // ---- next-state helpers
    wire [8:0]  adl_x   = {1'b0, adl} + {1'b0, x};
    wire [8:0]  adl_y   = {1'b0, adl} + {1'b0, y};
    wire [8:0]  pl_y    = {1'b0, pl} + {1'b0, y};
    wire [15:0] pc_inc  = r_pc + 16'd1;
    wire [8:0]  br_sum  = {1'b0, pc_inc[7:0]} + {1'b0, d_in};
    wire        ab_wr_pc = (ab_op >= 4'd7) && (ab_op <= 4'd10);

    always @(posedge clk) begin
        if (reset) begin
            x <= 8'd0; y <= 8'd0; s <= 8'd0; r_pc <= 16'd0;
            adl <= 8'd0; adh <= 8'd0; pl <= 8'd0;
            carry_q <= 1'b0; br_sign <= 1'b0;
        end else begin
            if (x_we) x <= wdata;
            if (y_we) y <= wdata;

            case (s_op)
                2'd1: s <= s - 8'd1;
                2'd2: s <= s + 8'd1;
                2'd3: s <= x;
                default: ;
            endcase

            if (!ab_wr_pc) begin
                case (pc_op)
                    2'd1: r_pc <= pc_inc;
                    2'd2: r_pc[7:0]  <= d_in;
                    2'd3: r_pc[15:8] <= d_in;
                    default: ;
                endcase
            end

            case (ab_op)
                4'd1:  adl <= d_in;
                4'd2:  adh <= d_in;
                4'd3:  begin adl <= adl_x[7:0]; carry_q <= adl_x[8]; end
                4'd4:  begin adl <= adl_y[7:0]; carry_q <= adl_y[8]; end
                4'd5:  adh <= adh + {7'd0, carry_q};
                4'd6:  adl <= adl + 8'd1;
                4'd7:  r_pc <= {d_in, adl};
                4'd8:  r_pc <= {adh, adl};
                4'd9:  begin
                    r_pc    <= {pc_inc[15:8], br_sum[7:0]};
                    br_sign <= d_in[7];
                    carry_q <= br_sum[8] ^ d_in[7];
                end
                4'd10: r_pc[15:8] <= br_sign ? (r_pc[15:8] - 8'd1) : (r_pc[15:8] + 8'd1);
                4'd11: begin pl <= d_in; adl <= adl + 8'd1; end
                4'd12: begin adh <= d_in; adl <= pl; end
                4'd13: begin adh <= d_in; adl <= pl_y[7:0]; carry_q <= pl_y[8]; end
                4'd14: begin adh <= d_in; adl <= adl_x[7:0]; carry_q <= adl_x[8]; end
                4'd15: begin adh <= d_in; adl <= adl_y[7:0]; carry_q <= adl_y[8]; end
                default: ;
            endcase
        end
    end
endmodule
