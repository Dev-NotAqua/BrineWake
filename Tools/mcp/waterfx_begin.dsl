(event EventBeginPlay
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Scan" :Time (Variables|Default|GetRescanSeconds) :bLooping true :bMaxOncePerFrame false :InitialStartDelay 1.0 :InitialStartDelayVariance 0.0))
