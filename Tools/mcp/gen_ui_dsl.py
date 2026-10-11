"""Writes frontend.dsl (widget logic) and frontend_actor.dsl (level actor that shows the menu)."""
COLOURS = [(0.62, 0.08, 0.07), (0.06, 0.14, 0.40), (0.14, 0.36, 0.14), (0.80, 0.56, 0.06), (0.34, 0.34, 0.36), (0.85, 0.30, 0.34)]
W = "Variables|WBP_BW_FrontEnd|"


def pick(channel):
    expr = str(COLOURS[-1][channel])
    for i in range(len(COLOURS) - 2, -1, -1):
        expr = "(select (== i %d) %s %s)" % (i, COLOURS[i][channel], expr)
    return expr


def page(n):
    return "(Switcher|SetActiveWidgetIndex :self (%sGetPages) :Index %d)" % (W, n)


dsl = """
(event UserInterface|EventConstruct
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (Input|SetInputModeUIOnly :PlayerController pc)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor true)
  (bind cam (Actor|GetActorOfClass :ActorClass "/Script/Engine.CameraActor"))
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget cam :BlendTime 0.0))

(event OnClicked(BtnPlay)
  %(p1)s)

(event OnClicked(BtnQuit)
  (Game|QuitGame))

(event OnClicked(BtnNext)
  (bind cur (Variables|Default|GetPirateIndex))
  (bind n (select (>= cur 5) 0 (+ cur 1)))
  (Variables|Default|SetPirateIndex n)
  (Switcher|SetActiveWidgetIndex :self (%(w)sGetPirateCards) :Index n))

(event OnClicked(BtnPrev)
  (bind cur (Variables|Default|GetPirateIndex))
  (bind n (select (<= cur 0) 5 (- cur 1)))
  (Variables|Default|SetPirateIndex n)
  (Switcher|SetActiveWidgetIndex :self (%(w)sGetPirateCards) :Index n))

(event OnClicked(BtnPirateOk)
  %(p2)s)

(event OnClicked(BtnPirateBack)
  %(p0)s)

(event OnClicked(BtnSloop)
  (Variables|Default|SetShipIndex 0)
  (Switcher|SetActiveWidgetIndex :self (%(w)sGetShipCards) :Index 0))

(event OnClicked(BtnBrig)
  (Variables|Default|SetShipIndex 1)
  (Switcher|SetActiveWidgetIndex :self (%(w)sGetShipCards) :Index 1))

(event OnClicked(BtnShipBack)
  %(p1)s)

(event OnClicked(BtnSail)
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (bind ch (Game|GetPlayerCharacter :PlayerIndex 0))
  (bind i (Variables|Default|GetPirateIndex))
  (bind tint (Math|Vector|MakeVector :X %(r)s :Y %(g)s :Z %(b)s))
  (Rendering|Material|SetVectorParameterValueonMaterials :self (Class|Character|GetMesh :self ch) :ParameterName "Paint Tint" :ParameterValue tint)
  (Input|SetInputModeGameOnly :PlayerController pc)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor false)
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget ch :BlendTime 2.0)
  (Widget|RemovefromParent :self self))
""" % {"p0": page(0), "p1": page(1), "p2": page(2), "w": W, "r": pick(0), "g": pick(1), "b": pick(2)}
open("frontend.dsl", "w", encoding="utf-8").write(dsl)
open("frontend_actor.dsl", "w", encoding="utf-8").write("""
(event EventBeginPlay
  (bind w (UserInterface|CreateWidget :Class "/Game/Brinewake/UI/WBP_BW_FrontEnd.WBP_BW_FrontEnd_C" :OwningPlayer (Game|GetPlayerController :PlayerIndex 0)))
  (UserInterface|Viewport|AddtoViewport :self w))
""")
print("written")
