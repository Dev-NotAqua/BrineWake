
(event UserInterface|EventConstruct
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (Input|SetInputModeUIOnly :PlayerController pc)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor true)
  (bind cam (Actor|GetActorOfClass :ActorClass "/Script/Engine.CameraActor"))
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget cam :BlendTime 0.0))

(event OnClicked(BtnPlay)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPages) :Index 1))

(event OnClicked(BtnQuit)
  (Game|QuitGame))

(event OnClicked(BtnNext)
  (bind cur (Variables|Default|GetPirateIndex))
  (bind n (select (>= cur 5) 0 (+ cur 1)))
  (Variables|Default|SetPirateIndex n)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPirateCards) :Index n))

(event OnClicked(BtnPrev)
  (bind cur (Variables|Default|GetPirateIndex))
  (bind n (select (<= cur 0) 5 (- cur 1)))
  (Variables|Default|SetPirateIndex n)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPirateCards) :Index n))

(event OnClicked(BtnPirateOk)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPages) :Index 2))

(event OnClicked(BtnPirateBack)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPages) :Index 0))

(event OnClicked(BtnSloop)
  (Variables|Default|SetShipIndex 0)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetShipCards) :Index 0))

(event OnClicked(BtnBrig)
  (Variables|Default|SetShipIndex 1)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetShipCards) :Index 1))

(event OnClicked(BtnShipBack)
  (Switcher|SetActiveWidgetIndex :self (Variables|WBP_BW_FrontEnd|GetPages) :Index 1))

(event OnClicked(BtnSail)
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (bind ch (Game|GetPlayerCharacter :PlayerIndex 0))
  (bind i (Variables|Default|GetPirateIndex))
  (bind tint (Math|Vector|MakeVector :X (select (== i 0) 0.62 (select (== i 1) 0.06 (select (== i 2) 0.14 (select (== i 3) 0.8 (select (== i 4) 0.34 0.85))))) :Y (select (== i 0) 0.08 (select (== i 1) 0.14 (select (== i 2) 0.36 (select (== i 3) 0.56 (select (== i 4) 0.34 0.3))))) :Z (select (== i 0) 0.07 (select (== i 1) 0.4 (select (== i 2) 0.14 (select (== i 3) 0.06 (select (== i 4) 0.36 0.34)))))))
  (Rendering|Material|SetVectorParameterValueonMaterials :self (Class|Character|GetMesh :self ch) :ParameterName "Paint Tint" :ParameterValue tint)
  (Input|SetInputModeGameOnly :PlayerController pc)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor false)
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget ch :BlendTime 2.0)
  (Widget|RemovefromParent :self self))
