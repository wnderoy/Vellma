function fib(n: nat): nat
{
   if n == 0 then 0 else
   if n == 1 then 1 else
                  fib(n - 1) + fib(n - 2)
}

method fibonacci1(n:nat) returns (f:nat)
ensures f==fib(n)
{
}

method fibonacci2(n:nat) returns (f:nat)
ensures f==fib(n)
{
}

method fibonacci3(n:nat) returns (f:nat)
ensures f==fib(n)
{
}

