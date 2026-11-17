// Driver for the Dormann functional test (Homer). Runs until the program traps (the same opcode-fetch address twice in a row:
// 'jmp *' is how the test reports pass or fail) or +MAXCLK=<n> clocks. Prints 'TRAP pc=XXXX clocks=N' or 'TIMEOUT clocks=N',
// and 'bus_conflict seen K times' as a separate line; sw/dormann/check_trap.py judges it (pass = trap at 3469h).
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "Vtb_top.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    unsigned long long maxclk = 2000000000ULL;
    for (int i = 1; i < argc; i++)
        if (!strncmp(argv[i], "+MAXCLK=", 8)) maxclk = strtoull(argv[i] + 8, nullptr, 10);
    Vtb_top* top = new Vtb_top;
    top->clk = 0; top->res_n = 0; top->eval();
    for (int e = 0; e < 8; e++) { top->clk = 1; top->eval(); top->clk = 0; top->eval(); }   // reset held for 8 clocks
    top->res_n = 1; top->eval();
    unsigned long long cyc = 0, conflicts = 0;
    int last = -1;
    for (;;) {
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
        cyc++;
        if (top->bus_conflict) conflicts++;
        if (top->sync) {                                    // an opcode fetch: a is its address
            int pc = top->a;
            if (pc == last) { printf("bus_conflict seen %llu times\nTRAP pc=%04X clocks=%llu\n", conflicts, pc, cyc); break; }
            last = pc;
        }
        if (cyc >= maxclk) { printf("bus_conflict seen %llu times\nTIMEOUT clocks=%llu\n", conflicts, cyc); break; }
    }
    delete top;
    return 0;
}
