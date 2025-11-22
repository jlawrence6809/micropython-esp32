grammar HomeAutomation;

// Parser rules
expr: ternaryExpr;
ternaryExpr
 : logicalOrExpr (QUESTION expr COLON expr)?
 ;

logicalOrExpr
 : logicalAndExpr (OR logicalAndExpr)*
 ;

logicalAndExpr
 : comparisonExpr (AND comparisonExpr)*
 ;

comparisonExpr
 : primaryExpr (( COMPARISON ) primaryExpr)*
 ;

// Define an assignment expression
assignmentExpr
 : IDENTIFIER ASSIGNMENT expr
 ;

primaryExpr
 : NUMBER
 | IDENTIFIER
 | HOUR_MINUTE
 | '(' expr ')'
 | NOT primaryExpr
 | assignmentExpr
 | BOOLEAN
 ;



// Lexer rules
NUMBER: [0-9]+ ('.' [0-9]+)?;
HOUR_MINUTE: '@' [0-9]+ ':' [0-9]+;
BOOLEAN: 'true' | 'false';
IDENTIFIER: [a-zA-Z_][a-zA-Z_0-9]*;
QUESTION: '?'; // Add this line
COLON: ':';    // Add this line
AND: '&';
OR: '|';
NOT: '!';
ASSIGNMENT: '=';
COMPARISON: '==' | '!=' | '>' | '<';
WS: [ \t\r\n]+ -> skip; // skip whitespace


