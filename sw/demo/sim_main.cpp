// Driver for the 6502 demo (Homer): prints every byte written to the console port, stops when the program spins ('jmp *': the same
// opcode-fetch address twice in a row) or at +MAXCLK=<n>. Last lines: 'bus_conflict seen K times' and 'TRAP pc=XXXX clocks=N' or 'TIMEOUT clocks=N'.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "Vtb_top.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    unsigned long long maxclk = 20000000ULL;
    for (int i = 1; i < argc; i++)
        if (!strncmp(argv[i], "+MAXCLK=", 8)) maxclk = strtoull(argv[i] + 8, nullptr, 10);
    Vtb_top* top = new Vtb_top;
    top->clk = 0; top->res_n = 0; top->eval();
    for (int e = 0; e < 8; e++) { top->clk = 1; top->eval(); top->clk = 0; top->eval(); }
    top->res_n = 1; top->eval();
    unsigned long long cyc = 0, conflicts = 0;
    int last = -1, nl = 0;
    for (;;) {
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
        cyc++;
        if (top->bus_conflict) conflicts++;
        if (top->con_strobe) { putchar(top->con_data); nl = (top->con_data == '\n'); }
        if (top->sync) {
            int pc = top->a;
            if (pc == last) { printf("%sbus_conflict seen %llu times\nTRAP pc=%04X clocks=%llu\n", nl ? "" : "\n", conflicts, pc, cyc); break; }
            last = pc;
        }
        if (cyc >= maxclk) { printf("%sbus_conflict seen %llu times\nTIMEOUT clocks=%llu\n", nl ? "" : "\n", conflicts, cyc); break; }
    }
    delete top;
    return 0;
}
