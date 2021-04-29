from typing import Set,Dict,List
from copy import deepcopy
from collections import namedtuple

# Type Aliases
Rules = Dict[str,List[List[str]]]

# Constants
EOF = "$"
EPSILON = "ε"
START = "S0"

class Grammar:
  def __init__(self, terms: Set[str], nonterms: Set[str],
               productions: Rules, start: str):
    self.terminals = terms
    self.nonTerminals = nonterms
    self.productions = productions
    self.startSymbol = start
    self.analyze()
  
  # return the number of production rules
  def __len__(self):
    return sum(len(val) for _, val in self.productions.items())

  def productOf(self, sym: str):
    if sym in self.nonTerminals:
      return self.productions[sym]
    else:
      return None

  def isNullable(self, x: str):
    if x in self.nullable:
      return True
    else:
      return False
  
  def allNullable(self, xs: List[str]):
    return all(self.isNullable(x) for x in xs)
  
  def firstOf(self, x: str):
    return self.first[x]

  def firstOfAll(self, xs: List[str]):
    res = set()
    for x in xs:
      res |= self.firstOf(x)
      if not self.isNullable(x):
        break
    return res

  def followOf(self, x: str):
    return self.follow[x]

  def followOfAll(self, xs: List[str]):
    print("followOfAll")
    res = set()
    for x in reversed(xs):
      res |= self.followOf(x)
      print(x,res)
      if not self.isNullable(x):
        break
    return res


  # Generate nullable/first/follow table
  def analyze(self):
    nullable = {EPSILON}
    update = True
    while update:
      update = False
      for nt in self.nonTerminals:
        if nt not in nullable:
          for rhs in self.productions[nt]:
            if all(sym in nullable for sym in rhs):
              update = True
              nullable.add(nt)
    self.nullable = nullable
    
    first = {nt : set() for nt in self.nonTerminals}
    for t in self.terminals:
      first[t] = {t}
    update = True
    while update:
      update = False
      for nt in self.nonTerminals:
        for rhs in self.productions[nt]:
          cascade = True
          temp = set()
          i = 0
          while i < len(rhs) and cascade:
            if rhs[i] not in nullable:
              cascade = False
            if rhs[i] in first:
              temp |= first[rhs[i]]
            i += 1

          if nt in first:
            if not temp.issubset(first[nt]):
              update = True
              first[nt] |= temp

    for nt in self.nonTerminals:
      if nt not in first:
        first[nt] = set()
    self.first = first

    follow = {nt : set() for nt in self.nonTerminals}
    for t in self.terminals:
      follow[t] = set()
    
    update = True
    while update:
      update = False
      for nt in self.nonTerminals:
        for rhs in self.productions[nt]:
          for i, sym in enumerate(rhs):
            # last symbol or all following symbols nullable
            if all(q in nullable for q in rhs[i+1:]):
              if not follow[nt].issubset(follow[sym]):
                update = True
                follow[sym] |= follow[nt]
            for j in range(i+1, len(rhs)):
              if all(p in nullable for p in rhs[i+1:j]):
                if not first[rhs[j]].issubset(follow[sym]):
                  update = True
                  follow[sym] |= first[rhs[j]]
    self.follow = follow


if __name__ == "__main__":
  print("Grammar...")

  terms1 = {"LEFT_PAREN", "RIGHT_PAREN", "ID", "MUL_OP", "DIV_OP",
            "PLUS_OP", "MINUS_OP", EPSILON}
  nonterms1 = {"E", "E'", "T", "T'", "F"}
  productions1 = {"E":  [["T","E'"]],
                  "E'": [["PLUS_OP", "T", "E'"], [EPSILON]],
                  "T":  [["F", "T'"]],
                  "T'": [["MUL_OP", "F", "T'"], [EPSILON]],
                  "F":  [["LEFT_PAREN", "E", "RIGHT_PAREN"], ["ID"]]}
  start1 = "E"
  g1 = Grammar(terms1, nonterms1, productions1, start1)
  g1.analyze()
  print("g1 nullable:",g1.nullable)
  print("g1 first:",g1.first)
  print("g1 follow:",g1.follow)


  symstr1 = [ EPSILON, "E'", "T"]
  print("string {} first: {}".format(list(reversed(symstr1)), g1.followOfAll(list(reversed(symstr1)))))
  print("string {} follow: {}".format(symstr1, g1.followOfAll(symstr1)))