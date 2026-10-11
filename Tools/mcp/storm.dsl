(event EventTick (DeltaSeconds)
  (Transformation|AddActorWorldOffset :DeltaLocation (* (Transformation|GetActorForwardVector) (* (Variables|Default|GetDriftSpeed) DeltaSeconds)))
  (Transformation|AddActorWorldRotation :DeltaRotation (Math|Rotator|MakeRotator :Yaw (* (Variables|Default|GetTurnRate) DeltaSeconds)))
  (bind loc (Transformation|GetActorLocation))
  (Rendering|Material|SetVectorParameterValue
    :Collection "/Game/Brinewake/Ocean/MPC_BW_Sea.MPC_BW_Sea"
    :ParameterName "StormShape"
    :ParameterValue (Utilities|Struct|MakeLinearColor :R (.x loc) :G (.y loc) :B (Variables|Default|GetRadius) :A (Variables|Default|GetIntensity)))
  (bind f (- (Variables|Default|GetFlash) (* DeltaSeconds 5.0)))
  (if (< (Math|Random|RandomFloat) (* DeltaSeconds (Variables|Default|GetLightningRate)))
    (Variables|Default|SetFlash 1.0)
    (else
      (Variables|Default|SetFlash (select (< f 0.0) 0.0 f))))
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetLightning) :NewIntensity (* (Variables|Default|GetFlash) (Variables|Default|GetLightningPeak)))
  (bind pawn (Game|GetPlayerPawn :PlayerIndex 0))
  (Utilities|IsValid pawn
    (:"Is Valid"
      (bind pl (Transformation|GetActorLocation :self pawn))
      (bind dx (- (.x pl) (.x loc)))
      (bind dy (- (.y pl) (.y loc)))
      (bind r (Variables|Default|GetRadius))
      (if (< (+ (* dx dx) (* dy dy)) (* r r))
        (Transformation|SetWorldLocation :self (Variables|Default|GetRain) :NewLocation (Math|Vector|MakeVector :X (.x pl) :Y (.y pl) :Z (+ (.z pl) 1500.0)) :bSweep false :bTeleport true)
        (else
          (Transformation|SetWorldLocation :self (Variables|Default|GetRain) :NewLocation (Math|Vector|MakeVector :X (.x loc) :Y (.y loc) :Z -900000.0) :bSweep false :bTeleport true))))
    (:"Is Not Valid")))
