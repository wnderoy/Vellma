// RUN: %testDafnyForEachCompiler --refresh-exit-code=0 "%s" -- --relax-definite-assignment

// This file shows an example program that uses both refinement and :autocontracts
// specify a class that stores a set of things that can be retrieved using a query.
//
// (For another example that uses these features, see Test/dafny3/CachedContainer.dfy.)

abstract module AbstractInterface {
  class {:autocontracts} StoreAndRetrieve<Thing(==)> {
    ghost var Contents: set<Thing>
    ghost predicate Valid() {
      Valid'()
    }
    ghost predicate {:autocontracts false} Valid'()
      reads this, Repr
    constructor Init()
      ensures Contents == {}
    method Store(t: Thing)
      ensures Contents == old(Contents) + {
}
    method Retrieve(matchCriterion: Thing -> bool) returns (thing: Thing)
      requires exists t :: t in Contents && matchCriterion(t)
      ensures Contents == old(Contents)
      ensures thing in Contents && matchCriterion(thing)
  }
}

abstract module A refines AbstractInterface {
}

abstract module B refines A {
  class StoreAndRetrieve<Thing(==)> ... {
    var arr: seq<Thing>
    ghost predicate Valid'...
    {
      Contents == set x | x in arr
    }
    constructor Init...
    {
      arr := [];
      new;
    }
    method Store...
    {
      arr := arr + [t];
      ...;
    }
    method Retrieve...
    {
      var i := 0;
      while (i < |arr|)
      {
        if matchCriterion(arr[i]) {
          break;
        }
        i := i + 1;
      }
      var k := arr[i];
      ...;
      var a: seq<Thing> :| assume Contents == set x | x in a;
      arr := a;
    }
  }
}

module abC refines B { // TODO module C causes Go to fail
  class StoreAndRetrieve<Thing(==)> ... {
    method Retrieve...
    {
      ...;
      var a := [thing] + arr[..i] + arr[i+1..];  // LRU behavior
    }
  }
}

abstract module AbstractClient {
  import S : AbstractInterface

  method Test() {
}
}

module Client refines AbstractClient {
  import S = abC
  method Main() {
}
}

