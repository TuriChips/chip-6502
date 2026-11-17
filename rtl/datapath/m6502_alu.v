// Ada: 6502 accumulator, status flags and the ALU. Ports and op table: docs/blocks.md section 3 (chip-6502#9).
// Decimal ADC/SBC follow spec section 6 exactly (NMOS N V Z, for every operand byte).
module m6502_alu (
    input  wire       clk,
    input  wire       reset,
    input  wire [4:0] op,
    input  wire [7:0] a_in,
    input  wire [7:0] b,
    input  wire       a_we,
    input  wire       f_we,
    input  wire       pull_p,
    input  wire       push_b,
    output wire [7:0] a_out,
    output wire [7:0] p_push,
    output wire [3:0] flags,        // {N, V, Z, C}
    output wire [7:0] result
);
    reg [7:0] a;
    reg       fn, fv, fd, fi, fz, fc;

    assign a_out  = a;
    assign p_push = {fn, fv, 1'b1, push_b, fd, fi, fz, fc};
    assign flags  = {fn, fv, fz, fc};

    // ---- combinational result and next flag values
    reg [7:0] res;
    reg       n_n, n_v, n_d, n_i, n_z, n_c;
    reg       u_n, u_v, u_d, u_i, u_z, u_c;   // flags this op updates
    reg       wr_a;
    reg [8:0] t;
    reg [7:0] bb;
    // decimal work
    reg [4:0] lo5;
    reg       hc;
    reg [3:0] lo;
    reg [7:0] x, y;
    reg [8:0] t9, t2;
    reg [4:0] dlo;
    reg [9:0] dt;
    reg       hb;

    always @* begin
        res = a_in; n_n = fn; n_v = fv; n_d = fd; n_i = fi; n_z = fz; n_c = fc;
        u_n = 1'b0; u_v = 1'b0; u_d = 1'b0; u_i = 1'b0; u_z = 1'b0; u_c = 1'b0;
        wr_a = 1'b1;
        t = 9'd0; bb = 8'd0; lo5 = 5'd0; hc = 1'b0; lo = 4'd0; x = 8'd0; y = 8'd0;
        t9 = 9'd0; t2 = 9'd0; dlo = 5'd0; dt = 10'd0; hb = 1'b0;
        case (op)
            5'd1: begin                                              // ADC
                t = {1'b0, a_in} + {1'b0, b} + {8'd0, fc};
                res = t[7:0];
                n_n = t[7]; n_v = (~(a_in[7] ^ b[7])) & (a_in[7] ^ t[7]); n_z = (t[7:0] == 8'd0); n_c = t[8];
                if (fd) begin
                    lo5 = {1'b0, a_in[3:0]} + {1'b0, b[3:0]} + {4'd0, fc};
                    hc  = (lo5 >= 5'd10);
                    lo  = hc ? (lo5[3:0] + 4'd6) : lo5[3:0];
                    x   = {a_in[7:4], lo};
                    y   = {b[7:4], hc ? 4'hF : 4'h0};
                    t9  = {1'b0, x} + {1'b0, y} + {8'd0, hc};
                    n_n = t9[7];
                    n_v = (~(x[7] ^ y[7])) & (x[7] ^ t9[7]);
                    if (t9[8] || t9[7:0] >= 8'hA0) begin
                        t2  = {1'b0, t9[7:0]} + 9'h060;
                        res = t2[7:0];
                        n_c = t9[8] | t2[8];
                    end else begin
                        res = t9[7:0];
                        n_c = t9[8];
                    end
                    // N V as above, Z from the binary sum (already in n_z)
                end
                u_n = 1'b1; u_v = 1'b1; u_z = 1'b1; u_c = 1'b1;
            end
            5'd2: begin                                              // SBC
                bb = ~b;
                t = {1'b0, a_in} + {1'b0, bb} + {8'd0, fc};
                res = t[7:0];
                n_n = t[7]; n_v = (~(a_in[7] ^ bb[7])) & (a_in[7] ^ t[7]); n_z = (t[7:0] == 8'd0); n_c = t[8];
                if (fd) begin                                        // only A is decimal
                    dlo = {1'b0, a_in[3:0]} - {1'b0, b[3:0]} - {4'd0, ~fc};   // -16..15 as 5-bit two's complement
                    hb  = dlo[4];
                    lo  = hb ? (dlo[3:0] - 4'd6) : dlo[3:0];
                    dt  = {2'b00, a_in[7:4], lo} - {2'b00, b[7:4], hb ? 4'hF : 4'h0} - {9'd0, hb};
                    if (dt[9]) dt = dt - 10'h060;
                    res = dt[7:0];
                end
                u_n = 1'b1; u_v = 1'b1; u_z = 1'b1; u_c = 1'b1;
            end
            5'd3: begin res = a_in & b; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // AND
            5'd4: begin res = a_in | b; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // ORA
            5'd5: begin res = a_in ^ b; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // EOR
            5'd6: begin                                              // CMP, CPX, CPY
                t = {1'b0, a_in} + {1'b0, ~b} + 9'd1;
                res = t[7:0]; wr_a = 1'b0;
                n_n = res[7]; n_z = (res == 8'd0); n_c = t[8];
                u_n = 1'b1; u_z = 1'b1; u_c = 1'b1;
            end
            5'd7: begin                                              // BIT
                res = a_in & b; wr_a = 1'b0;
                n_n = b[7]; n_v = b[6]; n_z = (res == 8'd0);
                u_n = 1'b1; u_v = 1'b1; u_z = 1'b1;
            end
            5'd8:  begin res = {b[6:0], 1'b0}; n_c = b[7]; u_c = 1'b1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end  // ASL
            5'd9:  begin res = {1'b0, b[7:1]}; n_c = b[0]; u_c = 1'b1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end  // LSR
            5'd10: begin res = {b[6:0], fc};   n_c = b[7]; u_c = 1'b1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end  // ROL
            5'd11: begin res = {fc, b[7:1]};   n_c = b[0]; u_c = 1'b1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end  // ROR
            5'd12: begin res = b + 8'd1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // INC
            5'd13: begin res = b - 8'd1; u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // DEC
            5'd14: begin res = b;        u_n = 1'b1; u_z = 1'b1; n_n = res[7]; n_z = (res == 8'd0); end   // LD
            5'd15: begin wr_a = 1'b0; n_c = 1'b0; u_c = 1'b1; end    // CLC
            5'd16: begin wr_a = 1'b0; n_c = 1'b1; u_c = 1'b1; end    // SEC
            5'd17: begin wr_a = 1'b0; n_i = 1'b0; u_i = 1'b1; end    // CLI
            5'd18: begin wr_a = 1'b0; n_i = 1'b1; u_i = 1'b1; end    // SEI
            5'd19: begin wr_a = 1'b0; n_d = 1'b0; u_d = 1'b1; end    // CLD
            5'd20: begin wr_a = 1'b0; n_d = 1'b1; u_d = 1'b1; end    // SED
            5'd21: begin wr_a = 1'b0; n_v = 1'b0; u_v = 1'b1; end    // CLV
            default: begin wr_a = 1'b0; end                          // 0 and 22..31: nothing
        endcase
    end

    assign result = res;

    always @(posedge clk) begin
        if (reset) begin
            a <= 8'd0;
            fn <= 1'b0; fv <= 1'b0; fd <= 1'b0; fi <= 1'b1; fz <= 1'b0; fc <= 1'b0;
        end else begin
            if (a_we && wr_a) a <= res;
            if (pull_p) begin
                fn <= b[7]; fv <= b[6]; fd <= b[3]; fi <= b[2]; fz <= b[1]; fc <= b[0];
            end else if (f_we) begin
                if (u_n) fn <= n_n;
                if (u_v) fv <= n_v;
                if (u_d) fd <= n_d;
                if (u_i) fi <= n_i;
                if (u_z) fz <= n_z;
                if (u_c) fc <= n_c;
            end
        end
    end
endmodule
