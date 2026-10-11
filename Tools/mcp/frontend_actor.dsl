
(event EventBeginPlay
  (bind w (UserInterface|CreateWidget :Class "/Game/Brinewake/UI/WBP_BW_FrontEnd.WBP_BW_FrontEnd_C" :OwningPlayer (Game|GetPlayerController :PlayerIndex 0)))
  (UserInterface|Viewport|AddtoViewport :self w))
