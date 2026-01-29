// Simple test file for code review
function add(a, b) {
    // Bug: no type checking
    return a + b;
}

function divide(x, y) {
    // Bug: no division by zero check
    return x / y;
}

// Unused variable
const unused = "I am not used anywhere";

console.log(add(1, 2)); // trigger review
console.log(divide(10, 0)); // This will return Infinity!
// trigger ollama review
