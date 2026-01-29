// src/bad-legacy.ts
// TEST FILE: Intentionally bad code to test AI Agents

export function processUserData(users: any) {
  let results = []; // VIOLATION: let usage
  for (let i = 0; i < users.length; i++) {
    // VIOLATION: Loop instead of map
    if (users[i].age > 18) {
       // VIOLATION: Direct SQL injection risk potential if this were a query
       results.push(users[i]); 
    }
  }
  return results;
}
