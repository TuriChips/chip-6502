// m6502_timing: T-state counter, RDY hold, reset sequence (spec sections 2, 4, 4.0, 5).
// Ports are ours to define (blocks.md leaves them open); the contract with m6502_control:
//   cyc_rd    this cycle is a read (rw = 1). RDY = 0 holds only a read cycle (spec 2, p.37).
//   cyc_last  this cycle is the instruction's last: when it completes, the next cycle is T0 (fetch).
//   t         0..6, the cycle of the current instruction (T0 = opcode fetch, sync = 1).
//   go        this cycle completes at the coming edge. 0 = held by RDY: the same cycle repeats, same
//             address, same sync; control must not change any state on an edge where go = 0.
//   rs        reset-sequence cycle: 0 = res_n is low (or just released, half a cycle), 1..7 = the seven
//             cycles after release (spec 4/5), 8 = not in reset (normal running). T0 of the first
//             instruction is the cycle after rs = 7.
// While rs != 8 control forces rw = 1, d_oe = 0, sync = 0 (spec 5).
module m6502_timing (
    input  wire       clk,
    input  wire       res_n,
    input  wire       rdy,
    input  wire       cyc_rd,
    input  wire       cyc_last,
    output wire [2:0] t,
    output wire       go,
    output wire [3:0] rs
);
    reg [2:0] t_r;
    reg [3:0] rs_r;

    wire running = (rs_r == 4'd8);
    // RDY holds a read cycle of the running CPU only; reset cycles and writes always complete
    assign go = ~running | ~cyc_rd | rdy;
    assign t  = running ? t_r : 3'd0;
    assign rs = res_n ? rs_r : 4'd0;

    always @(posedge clk) begin
        if (!res_n) begin
            t_r  <= 3'd0;
            rs_r <= 4'd0;
        end else if (!running) begin
            rs_r <= rs_r + 4'd1;           // 0 -> 1 on the first edge after release, ... 7 -> 8
            t_r  <= 3'd0;
        end else if (go) begin
            t_r <= cyc_last ? 3'd0 : t_r + 3'd1;
        end
    end
endmodule
