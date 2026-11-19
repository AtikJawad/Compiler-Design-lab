%{
/*
 * lexer.l  -  Lexical Analyzer (Scanner) written in Lex/Flex
 * Compiler Design Assignment 01 - Part (i)
 *
 * Language recognised: a small C-like language
 *   - Keywords    : int float if else while print
 *   - Identifiers : letter (letter | digit | _)*
 *   - Numbers     : integers and floating point (e.g. 42, 3.14)
 *   - Operators   : + - * / = == != < > <= >=
 *   - Delimiters  : ( ) { } ; ,
 *   - Comments    : // single line   and   / * multi line * /
 *   - Strings     : "..."
 *
 * Build : flex lexer.l && gcc lex.yy.c -o lexer
 * Run   : ./lexer input.txt
 */
#include <stdio.h>
#include <string.h>

int line_no   = 1;
int tok_count = 0;
int err_count = 0;

/* count of every token category, for the summary */
int n_kw = 0, n_id = 0, n_num = 0, n_op = 0, n_del = 0, n_str = 0;

/* very small symbol table for identifiers */
#define MAX_SYM 200
char symtab[MAX_SYM][64];
int  sym_count = 0;

int install_id(const char *name) {
    for (int i = 0; i < sym_count; i++)
        if (strcmp(symtab[i], name) == 0) return i;
    if (sym_count < MAX_SYM) {
        strncpy(symtab[sym_count], name, 63);
        symtab[sym_count][63] = '\0';
        return sym_count++;
    }
    return -1;
}

void emit(const char *type, const char *lexeme) {
    tok_count++;
    printf("| %-4d | %-14s | %-22s |\n", line_no, type, lexeme);
}
%}

%option noyywrap

DIGIT    [0-9]
LETTER   [a-zA-Z_]
ID       {LETTER}({LETTER}|{DIGIT})*
INT      {DIGIT}+
FLOAT    {DIGIT}+\.{DIGIT}+

%x COMMENT

%%

"//".*                      { /* single-line comment: ignore */ }
"/*"                        { BEGIN(COMMENT); }
<COMMENT>"*/"               { BEGIN(INITIAL); }
<COMMENT>\n                 { line_no++; }
<COMMENT>.                  { /* skip comment body */ }
<COMMENT><<EOF>>            { printf("| %-4d | %-14s | %-22s |\n", line_no, "ERROR", "unterminated comment");
                              err_count++; return 0; }

"int"|"float"|"if"|"else"|"while"|"print"   { n_kw++;  emit("KEYWORD", yytext); }

{ID}                        { n_id++;  install_id(yytext); emit("IDENTIFIER", yytext); }
{FLOAT}                     { n_num++; emit("FLOAT_CONST", yytext); }
{INT}                       { n_num++; emit("INT_CONST", yytext); }

\"[^\"\n]*\"                { n_str++; emit("STRING", yytext); }

"=="|"!="|"<="|">="         { n_op++;  emit("RELOP", yytext); }
"<"|">"                     { n_op++;  emit("RELOP", yytext); }
"="                         { n_op++;  emit("ASSIGN_OP", yytext); }
"+"|"-"|"*"|"/"             { n_op++;  emit("ARITH_OP", yytext); }

"("|")"|"{"|"}"|";"|","     { n_del++; emit("DELIMITER", yytext); }

[ \t\r]+                    { /* skip whitespace */ }
\n                          { line_no++; }

{DIGIT}+{LETTER}({LETTER}|{DIGIT})*  { err_count++; emit("ERROR(bad id)", yytext); }
.                           { err_count++; emit("ERROR(unknown)", yytext); }

%%

int main(int argc, char *argv[]) {
    if (argc > 1) {
        yyin = fopen(argv[1], "r");
        if (!yyin) { perror(argv[1]); return 1; }
    }

    printf("\n==================== LEXICAL ANALYSIS ====================\n");
    printf("+------+----------------+------------------------+\n");
    printf("| Line | Token Type     | Lexeme                 |\n");
    printf("+------+----------------+------------------------+\n");

    yylex();

    printf("+------+----------------+------------------------+\n");

    printf("\n==================== SUMMARY ====================\n");
    printf("Total tokens     : %d\n", tok_count);
    printf("  Keywords       : %d\n", n_kw);
    printf("  Identifiers    : %d\n", n_id);
    printf("  Constants      : %d\n", n_num);
    printf("  Strings        : %d\n", n_str);
    printf("  Operators      : %d\n", n_op);
    printf("  Delimiters     : %d\n", n_del);
    printf("Lexical errors   : %d\n", err_count);

    printf("\n==================== SYMBOL TABLE ====================\n");
    printf("+-------+----------------------+\n");
    printf("| Index | Identifier           |\n");
    printf("+-------+----------------------+\n");
    for (int i = 0; i < sym_count; i++)
        printf("| %-5d | %-20s |\n", i, symtab[i]);
    printf("+-------+----------------------+\n");
    return 0;
}
