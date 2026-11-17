// Ada: 64 KiB RAM for tests. Ports and timing: docs/blocks.md section 3 (chip-6502#9).
// rdata is combinational and always follows addr (a 6502 read cycle has no strobe). A write happens on the rising clk edge with we = 1.
// Bytes the INIT_FILE does not cover (and every byte if INIT_FILE is empty) read as 00.
module m6502_mem #(
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire [15:0] addr,
    input  wire        we,
    input  wire [7:0]  wdata,
    output wire [7:0]  rdata
);
    reg [7:0] mem [0:65535];
    integer i;

    initial begin
        for (i = 0; i < 65536; i = i + 1) mem[i] = 8'h00;
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
    end

    assign rdata = mem[addr];

    always @(posedge clk) begin
        if (we) mem[addr] <= wdata;
    end
endmodule
