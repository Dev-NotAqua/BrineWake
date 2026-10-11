import json
U="UMGToolSet.UMGToolSet."
OT="editor_toolset.toolsets.object.ObjectTools."
AS="editor_toolset.toolsets.asset.AssetTools."
BT="editor_toolset.toolsets.blueprint.BlueprintTools."
WB={"refPath":"/Game/Brinewake/UI/WBP_BW_FrontEnd.WBP_BW_FrontEnd"}
GOLD={"r":1.0,"g":0.80,"b":0.42,"a":1.0}
PARCH={"r":0.93,"g":0.88,"b":0.74,"a":1.0}
DIM={"r":0.62,"g":0.72,"b":0.72,"a":1.0}
PIRATES=[("MARLOWE REDTIDE","Gunner. Scarlet coat, short temper.",(0.62,0.08,0.07)),
         ("ISOLDE BLACKWATER","Navigator. Midnight blue, steady hand.",(0.06,0.14,0.40)),
         ("OLD TOBIAS FINCH","Cook. Moss green, older than the sea.",(0.14,0.36,0.14)),
         ("SERAPHINE GOLD","Quartermaster. Sun yellow, counts every coin.",(0.80,0.56,0.06)),
         ("BRAM ASHGROVE","Carpenter. Ash grey, fixes what you break.",(0.34,0.34,0.36)),
         ("NERISSA CORAL","Diver. Coral pink, lungs like a whale.",(0.85,0.30,0.34))]
SHIPS=[("SLOOP","1 to 2 pirates","One mast. Turns on a coin, slips over shallows, easy to sail alone."),
       ("BRIGANTINE","2 to 3 pirates","Two masts. Fastest with the wind behind her, four cannons, needs a crew.")]
def call(n,a): return execute_tool(n,json.dumps(a))
def setp(ref,vals): call(OT+"set_properties",{"instance":ref,"values":json.dumps(vals)})
def add(cls,name,parent=None,var=False):
    a={"widgetBlueprint":WB,"widgetClass":{"refPath":"/Script/UMG."+cls},"widgetDisplayName":name,"childIndex":-1}
    if parent: a["parentWidget"]=parent
    r=call(U+"AddWidget",a)["returnValue"]
    if var: call(U+"ToggleWidgetAsVariable",{"widgetBlueprint":WB,"widget":r["widget"],"bIsVariable":True})
    return r
def full(slot): setp(slot,{"layoutData":{"offsets":{"left":0,"top":0,"right":0,"bottom":0},"anchors":{"minimum":{"x":0,"y":0},"maximum":{"x":1,"y":1}},"alignment":{"x":0,"y":0}}})
def text(parent,name,s,size,colour,spacing=0,pad=8,wrap=0,just="Center",align="HAlign_Center"):
    t=add("TextBlock",name,parent)
    font=json.loads(call(OT+"get_properties",{"instance":t["widget"],"properties":["font"]})["returnValue"])["font"]
    font["size"]=size; font["letterSpacing"]=spacing
    v={"text":s,"font":font,"colorAndOpacity":{"specifiedColor":colour,"colorUseRule":"UseColor_Specified"},"justification":just,
       "shadowOffset":{"x":2,"y":3},"shadowColorAndOpacity":{"r":0,"g":0.03,"b":0.05,"a":0.75}}
    if wrap: v["autoWrapText"]=True; v["wrapTextAt"]=wrap
    setp(t["widget"],v)
    try: setp(t["slot"],{"padding":{"left":pad,"top":pad,"right":pad,"bottom":pad},"horizontalAlignment":align})
    except Exception: pass
    return t
def button(parent,name,label,size=30,width=420):
    b=add("Button",name,parent,var=True)
    setp(b["widget"],{"backgroundColor":{"r":0.03,"g":0.16,"b":0.19,"a":0.92}})
    try: setp(b["slot"],{"padding":{"left":10,"top":8,"right":10,"bottom":8},"horizontalAlignment":"HAlign_Center"})
    except Exception: pass
    t=text(b["widget"],name+"_Label",label,size,GOLD,spacing=120,pad=6)
    try: setp(t["slot"],{"padding":{"left":70,"top":10,"right":70,"bottom":10}})
    except Exception: pass
    return b
def column(parent,name):
    v=add("VerticalBox",name,parent)
    return v
def anchor(slot,ax,ay,px,py,alx,aly):
    setp(slot,{"layoutData":{"offsets":{"left":px,"top":py,"right":0,"bottom":0},"anchors":{"minimum":{"x":ax,"y":ay},"maximum":{"x":ax,"y":ay}},"alignment":{"x":alx,"y":aly}},"bAutoSize":True})
def card(parent,btn,title,line,stats,band,seed):
    b=add("Button",btn,parent,var=True)
    setp(b["widget"],{"backgroundColor":{"r":0.05,"g":0.09,"b":0.11,"a":0.96}})
    try: setp(b["slot"],{"padding":{"left":0,"top":0,"right":22,"bottom":0}})
    except Exception: pass
    v=add("VerticalBox",btn+"_Col",b["widget"])["widget"]
    hb=add("Border",btn+"_Band",v)
    setp(hb["widget"],{"brushColor":band,"padding":{"left":26,"top":16,"right":26,"bottom":16}})
    hv=add("VerticalBox",btn+"_BandCol",hb["widget"])["widget"]
    text(hv,btn+"_Title",title,34,PARCH,spacing=60,pad=2,just="Left",align="HAlign_Left")
    text(hv,btn+"_Line",line,17,PARCH,spacing=10,pad=2,wrap=330,just="Left",align="HAlign_Left")
    body=add("Border",btn+"_Body",v)
    setp(body["widget"],{"brushColor":{"r":0.03,"g":0.13,"b":0.16,"a":0.9},"padding":{"left":26,"top":26,"right":26,"bottom":34}})
    bv=add("VerticalBox",btn+"_BodyCol",body["widget"])["widget"]
    for i,(k,val) in enumerate(stats):
        text(bv,"%s_K%d"%(btn,i),k,14,DIM,spacing=260,pad=2,just="Left",align="HAlign_Left")
        text(bv,"%s_V%d"%(btn,i),val,24,GOLD,spacing=40,pad=2,just="Left",align="HAlign_Left")
    return b
def run():
    out={"err":[]}
    for w in call(U+"GetWidgets",{"widgetBlueprint":WB})["returnValue"]["widgets"]:
        if w["parent"]=="None":
            call(U+"RemoveWidget",{"widgetBlueprint":WB,"widget":w["widget"]})
    root=add("CanvasPanel","Root")["widget"]
    shade=add("Border","Shade",root)
    setp(shade["widget"],{"brushColor":{"r":0.0,"g":0.035,"b":0.05,"a":0.58}})
    full(shade["slot"])
    bar=add("Border","TopBar",root)
    setp(bar["widget"],{"brushColor":{"r":0.0,"g":0.02,"b":0.03,"a":0.72},"padding":{"left":90,"top":18,"right":90,"bottom":16}})
    setp(bar["slot"],{"layoutData":{"offsets":{"left":0,"top":0,"right":0,"bottom":74},"anchors":{"minimum":{"x":0,"y":0},"maximum":{"x":1,"y":0}},"alignment":{"x":0,"y":0}}})
    tabs=add("HorizontalBox","Tabs",bar["widget"])["widget"]
    for i,(n,c) in enumerate((("Pirate",DIM),("Discover",DIM),("Play",PARCH),("Progress",DIM),("Guilds",DIM))):
        text(tabs,"Tab_%d"%i,n,26,c,spacing=30,pad=14)
    who=text(root,"Who","Deckhand",20,PARCH,spacing=20)
    anchor(who["slot"],1,0,-90,24,1,0)
    pages=add("WidgetSwitcher","Pages",root,var=True)
    setp(pages["slot"],{"layoutData":{"offsets":{"left":90,"top":110,"right":90,"bottom":90},"anchors":{"minimum":{"x":0,"y":0},"maximum":{"x":1,"y":1}},"alignment":{"x":0,"y":0}}})
    P=pages["widget"]
    def page(name,center=False):
        o=add("Overlay","Page_"+name,P)
        c=add("VerticalBox","Col_"+name,o["widget"])
        try: setp(c["slot"],{"horizontalAlignment":"HAlign_Center" if center else "HAlign_Left","verticalAlignment":"VAlign_Center" if center else "VAlign_Top"})
        except Exception as e: out["err"].append(str(e)[:150])
        return c["widget"]
    c=page("Title",center=True)
    sign=add("Border","Title_Sign",c)
    setp(sign["widget"],{"brushColor":{"r":0.16,"g":0.09,"b":0.05,"a":0.94},"padding":{"left":70,"top":26,"right":70,"bottom":30}})
    sv=add("VerticalBox","Title_SignCol",sign["widget"])["widget"]
    text(sv,"Title_Name","BRINEWAKE",112,GOLD,spacing=380,pad=2)
    text(sv,"Title_Tag","salt   storm   fortune",24,PARCH,spacing=420,pad=2)
    g=add("Spacer","Title_Gap",c)
    try: setp(g["widget"],{"size":{"x":10,"y":46}})
    except Exception: pass
    button(c,"BtnPlay","BEGIN",32)
    button(c,"BtnQuit","EXIT TO DESKTOP",18)
    c=page("Pirate")
    text(c,"Pirate_Head","Choose Pirate",44,PARCH,spacing=20,just="Left",align="HAlign_Left")
    text(c,"Pirate_Sub","Pick who you were before the sea took your name.",20,DIM,spacing=10,pad=4,just="Left",align="HAlign_Left")
    row=add("HorizontalBox","Pirate_Row",c)
    try: setp(row["slot"],{"horizontalAlignment":"HAlign_Left","padding":{"left":0,"top":30,"right":0,"bottom":26}})
    except Exception: pass
    button(row["widget"],"BtnPrev","<",40)
    cards=add("WidgetSwitcher","PirateCards",row["widget"],var=True)
    for i,(nm,desc,col) in enumerate(PIRATES):
        b=add("Border","Pirate_%d"%i,cards["widget"])
        setp(b["widget"],{"brushColor":{"r":0.03,"g":0.13,"b":0.16,"a":0.94},"padding":{"left":0,"top":0,"right":0,"bottom":26}})
        v=add("VerticalBox","Pirate_%d_Col"%i,b["widget"])["widget"]
        band=add("Border","Pirate_%d_Band"%i,v)
        setp(band["widget"],{"brushColor":{"r":col[0],"g":col[1],"b":col[2],"a":0.95},"padding":{"left":40,"top":54,"right":40,"bottom":54}})
        text(band["widget"],"Pirate_%d_Name"%i,nm,38,PARCH,spacing=120)
        text(v,"Pirate_%d_Desc"%i,desc,22,PARCH,spacing=10,wrap=560,pad=22)
        text(v,"Pirate_%d_No"%i,"%d of %d"%(i+1,len(PIRATES)),15,DIM,spacing=200)
    button(row["widget"],"BtnNext",">",40)
    r2=add("HorizontalBox","Pirate_Buttons",c)["widget"]
    button(r2,"BtnPirateBack","BACK",20)
    button(r2,"BtnPirateOk","THIS IS ME",26)
    c=page("Ship")
    text(c,"Ship_Head","Select a Ship Type",44,PARCH,spacing=20,just="Left",align="HAlign_Left")
    row=add("HorizontalBox","Ship_Row",c)
    try: setp(row["slot"],{"horizontalAlignment":"HAlign_Left","padding":{"left":0,"top":30,"right":0,"bottom":22}})
    except Exception: pass
    card(row["widget"],"BtnSloop","Sloop","Turns on a coin, slips over shallows. Easy to sail alone.",(("CREW","1 to 2 pirates"),("MASTS","One"),("CANNONS","Two"),("BEST AT","Tight turns, hiding")),{"r":0.05,"g":0.42,"b":0.40,"a":0.96},1)
    card(row["widget"],"BtnBrig","Brigantine","Fastest with the wind behind her. Wants a crew.",(("CREW","2 to 3 pirates"),("MASTS","Two"),("CANNONS","Four"),("BEST AT","Open water chases")),{"r":0.36,"g":0.16,"b":0.46,"a":0.96},2)
    cards=add("WidgetSwitcher","ShipCards",c,var=True)
    try: setp(cards["slot"],{"horizontalAlignment":"HAlign_Left"})
    except Exception: pass
    for i,(nm,crew,desc) in enumerate(SHIPS):
        text(cards["widget"],"Ship_%d_Pick"%i,"Chosen:  "+nm+"   ("+crew+")",24,GOLD,spacing=40,just="Left",align="HAlign_Left")
    r2=add("HorizontalBox","Ship_Buttons",c)["widget"]
    button(r2,"BtnShipBack","BACK",20)
    button(r2,"BtnSail","SET SAIL",28)
    hint=text(root,"Hints","Click to select      Back to return      Brinewake early voyage build",15,DIM,spacing=40,just="Left")
    anchor(hint["slot"],0,1,90,-34,0,1)
    for v,t in (("PirateIndex","int"),("ShipIndex","int")):
        try: call(BT+"add_variable",{"blueprint":WB,"name":v,"type_name":t})
        except Exception as e: pass
    for b in ("BtnPlay","BtnQuit","BtnPrev","BtnNext","BtnPirateOk","BtnPirateBack","BtnSloop","BtnBrig","BtnSail","BtnShipBack"):
        try: call(U+"BindToEventProperty",{"widgetBlueprint":WB,"eventName":"OnClicked","propertyName":b,"propertyClass":{"refPath":"/Script/UMG.Button"}})
        except Exception as e: out["err"].append(b+" "+str(e)[:120])
    try: out["compile"]=call(U+"CompileWidgetBlueprint",{"widgetBlueprint":WB})["returnValue"]
    except Exception as e: out["compile"]=str(e)[:400]
    g={"refPath":WB["refPath"]+":EventGraph"}
    out["dsl"]=call(BT+"read_graph_dsl",{"graph":g})["returnValue"][:900]
    for f in ("Class|PlayerController|SetShowMouseCursor","Switcher|SetActiveWidgetIndex","Game|QuitGame","Input|SetInputModeGameOnly","Actor|GetActorOfClass"):
        try:
            p=call(BT+"get_node_type_pins",{"graph":g,"type_id":f})["returnValue"]
            out["pins "+f]=[x["name"] for x in p["input_pins"]]
        except Exception as e: out["pins "+f]=str(e)[:100]
    call(AS+"save_assets",{"asset_paths":["/Game/Brinewake/UI/WBP_BW_FrontEnd"]})
    return out
