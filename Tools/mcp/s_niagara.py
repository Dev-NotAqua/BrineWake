import json
NS='NiagaraToolsets.NiagaraToolset_System.'
AS='editor_toolset.toolsets.asset.AssetTools.'
V='/Game/Brinewake/VFX'
T='/Niagara/DefaultAssets/Templates/'
def call(n_,a): return execute_tool(n_,json.dumps(a))
def ref(sys,em='',script='',module='',inp=None): return {'system':sys,'emitterName':em,'scriptName':script,'moduleName':module,'rendererIndex':-1,'inputNameStack':inp or []}
F=lambda v: {'struct':{'refPath':'/Script/Niagara.NiagaraFloat'},'value':{'value':v}}
V3=lambda x,y,z: {'struct':{'refPath':'/Script/CoreUObject.Vector3f'},'value':{'x':x,'y':y,'z':z}}
C=lambda r,g,b,a: {'struct':{'refPath':'/Script/CoreUObject.LinearColor'},'value':{'r':r,'g':g,'b':b,'a':a}}
PS,PU,EU='ParticleSpawnScript','ParticleUpdateScript','EmitterUpdateScript'
def run():
    out={'err':[]}
    def setv(sys,em,script,module,names,val):
        try: call(NS+'SetStackInputData',{'stackInputRef':ref(sys,em,script,module,names),'inputData':val})
        except Exception as e:
            if len(out['err'])<14: out['err'].append(module+'/'+'/'.join(names)+' '+str(e)[:160])
    def new(name):
        if call(AS+'exists',{'path':V+'/'+name})['returnValue']: call(AS+'delete',{'path':V+'/'+name})
        call(NS+'CreateNiagaraSystem',{'assetName':name,'assetPath':V,'templateSystem':{'refPath':T+'Systems/DirectionalBurst.DirectionalBurst'}})
        sys={'refPath':V+'/'+name+'.'+name}
        for e in call(NS+'GetSystemSummary',{'system':sys})['returnValue']['emitters']:
            call(NS+'RemoveEmitter',{'emitterToRemove':ref(sys,e['emitterName'])})
        return sys
    def fountain(sys,em,rate,life,size,col,radius,cone,speed,grav,drag):
        call(NS+'AddEmitter',{'system':sys,'templateEmitter':{'refPath':T+'Emitters/Fountain.Fountain'},'emitterName':em})
        setv(sys,em,EU,'SpawnRate',['SpawnRate'],F(rate))
        setv(sys,em,PS,'InitializeParticle',['Lifetime Min'],F(life[0])); setv(sys,em,PS,'InitializeParticle',['Lifetime Max'],F(life[1]))
        setv(sys,em,PS,'InitializeParticle',['Uniform Sprite Size Min'],F(size[0])); setv(sys,em,PS,'InitializeParticle',['Uniform Sprite Size Max'],F(size[1]))
        setv(sys,em,PS,'InitializeParticle',['Color'],C(*col))
        setv(sys,em,PS,'ShapeLocation',['Sphere Radius'],F(radius))
        setv(sys,em,PS,'AddVelocity',['Cone Angle'],F(cone))
        setv(sys,em,PS,'AddVelocity',['Velocity Speed','Minimum'],F(speed[0])); setv(sys,em,PS,'AddVelocity',['Velocity Speed','Maximum'],F(speed[1]))
        setv(sys,em,PU,'GravityForce',['Gravity'],V3(0,0,grav))
        setv(sys,em,PU,'Drag',['Drag'],F(drag))
    s=new('NS_BW_WaterSpray')
    fountain(s,'Spray',24,(0.45,0.95),(5,15),(1,1,1,0.85),55,58,(170,430),-980,0.3)
    fountain(s,'Mist',7,(0.9,1.6),(40,95),(0.9,0.97,1.0,0.16),70,75,(40,120),-120,1.2)
    s2=new('NS_BW_Fire')
    fountain(s2,'Flames',42,(0.45,0.9),(16,38),(7.0,2.6,0.5,1.0),13,13,(60,150),130,1.2)
    fountain(s2,'Embers',7,(1.1,2.2),(1.5,3.5),(9.0,3.0,0.5,1.0),14,24,(90,240),45,0.3)
    fountain(s2,'Smoke',5,(1.8,3.0),(45,110),(0.09,0.08,0.08,0.22),12,10,(70,130),90,0.6)
    s3=new('NS_BW_Torch')
    fountain(s3,'Flames',26,(0.3,0.6),(7,18),(7.0,2.6,0.5,1.0),5,10,(40,95),120,1.2)
    fountain(s3,'Embers',3,(0.9,1.6),(1.0,2.5),(9.0,3.0,0.5,1.0),5,22,(60,160),40,0.3)
    s4=new('NS_BW_Fireflies')
    fountain(s4,'Flies',5,(4.0,7.0),(2.5,5.5),(2.2,3.6,0.5,1.0),520,180,(8,30),0,1.5)
    s5=new('NS_BW_Splash')
    fountain(s5,'Burst',110,(0.5,1.1),(6,20),(1,1,1,0.9),35,48,(260,620),-980,0.25)
    for n in ('NS_BW_WaterSpray','NS_BW_Fire','NS_BW_Torch','NS_BW_Fireflies','NS_BW_Splash'):
        try:
            st=call(NS+'GetSystemCompileState',{'system':{'refPath':V+'/'+n+'.'+n}})['returnValue']
            out[n]=str(st)[:120]
        except Exception as e: out[n]=str(e)[:120]
    call(AS+'save_assets',{'asset_paths':[V+'/'+n for n in ('NS_BW_WaterSpray','NS_BW_Fire','NS_BW_Torch','NS_BW_Fireflies','NS_BW_Splash')]})
    return out
