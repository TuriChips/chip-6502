// verilator lint_off UNOPTFLAT
// m6502_system: CPU + 64 KiB RAM + console port + stimulus inputs + bus_conflict (spec 7, blocks.md 1). Test fixture,
// not synthesized.
//
// Bus: the memory drives d_in in read cycles; the CPU drives d_out in write cycles (d_oe). `bus` is what is on the
// data bus: d_oe ? d_out : memory byte. bus_conflict = 1 when the CPU drives while this is a read cycle (d_oe & rw),
// the 8080-style "two drivers on at once" check. (spec 4.0 also compares d_oe = NOT rw every cycle in the tests.)
// Console: a write to CON_ADDR (default F001h) is not stored in RAM; con_data holds the byte and con_strobe pulses for
// one clock. Reads of CON_ADDR return RAM. RDY, IRQ, NMI and S.O. are plain inputs, driven by the testbench per the
// stimulus rules of spec 2 and 6.
module m6502_system #(
    parameter INIT_FILE = "",
    parameter [15:0] CON_ADDR = 16'hF001
) (
    input  wire        clk,
    input  wire        res_n,
    input  wire        rdy,
    input  wire        irq_n,
    input  wire        nmi_n,
    input  wire        so_n,
    // CPU pins brought out for tests
    output wire [15:0] a,
    output wire [7:0]  d_out,
    output wire        d_oe,
    output wire        rw,
    output wire        sync,
    output wire [7:0]  bus,
    output wire [7:0]  con_data,
    output wire        con_strobe,
    output wire        bus_conflict
);
    wire [7:0] mem_rdata;

    m6502 cpu (
        .clk(clk), .res_n(res_n), .a(a), .d_in(bus), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync),
        .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n)
    );

    wire write   = res_n & d_oe & ~rw;
    wire to_con  = write & (a == CON_ADDR);

    m6502_mem #(.INIT_FILE(INIT_FILE)) mem (
        .clk(clk), .addr(a), .we(write & ~to_con), .wdata(d_out), .rdata(mem_rdata)
    );

    assign bus = d_oe ? d_out : mem_rdata;
    assign bus_conflict = d_oe & rw;

    reg [7:0] con_r;
    reg       con_s;
    always @(posedge clk) begin
        if (!res_n) begin con_r <= 8'h00; con_s <= 1'b0; end
        else begin
            con_s <= to_con;
            if (to_con) con_r <= d_out;
        end
    end
    assign con_data   = con_r;
    assign con_strobe = con_s;
endmodule
