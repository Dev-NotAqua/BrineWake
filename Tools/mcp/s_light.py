import json
ST='editor_toolset.toolsets.scene.SceneTools.'
AT='editor_toolset.toolsets.actor.ActorTools.'
OT='editor_toolset.toolsets.object.ObjectTools.'
def call(n_,a): return execute_tool(n_,json.dumps(a))
def run():
    out={'err':[]}
    def setp(inst,vals,tag):
        for k,v in vals.items():
            try: call(OT+'set_properties',{'instance':inst,'values':json.dumps({k:v})})
            except Exception as e:
                if len(out['err'])<14: out['err'].append(tag+'.'+k+' '+str(e)[:110])
    for a in call(ST+'get_actors_in_folder',{'folder_path':'Sky','recursive':False})['returnValue']:
        r=a['refPath']
        if 'DirectionalLight' in r:
            c={'refPath':r+'.LightComponent0'}
            setp(c,{'bEnableLightShaftBloom':True,'bloomScale':0.2,'bloomThreshold':0.0,'bloomMaxBrightness':100.0,'bEnableLightShaftOcclusion':True,'occlusionMaskDarkness':0.55,
                    'occlusionDepthRange':100000.0,'volumetricScatteringIntensity':3.2,'lightSourceAngle':1.3,'bUseTemperature':True,'temperature':5400.0,'intensity':9.0},'sun')
            t=call(AT+'get_actor_transform',{'actor':a})['returnValue']
            out['sun_before']=t['rotation']
            t['rotation']['pitch']=__PITCH__
            t['rotation']['yaw']=__YAW__
            call(AT+'set_actor_transform',{'actor':a,'xform':t,'worldspace':True})
        elif 'HeightFog' in r:
            c={'refPath':r+'.HeightFogComponent0'}
            setp(c,{'bEnableVolumetricFog':True,'volumetricFogScatteringDistribution':0.82,'volumetricFogExtinctionScale':1.3,'volumetricFogDistance':14000.0,'fogDensity':0.008,'fogHeightFalloff':0.10,
                    'volumetricFogAlbedo':{'r':255,'g':246,'b':228,'a':255},'startDistance':0.0},'fog')
        elif 'SkyLight' in r:
            setp({'refPath':r+'.SkyLightComponent0'},{'bRealTimeCapture':True,'intensity':1.15},'sky')
    pps=call(ST+'find_actors',{'root':None,'name':'BW_PostProcess','actor_type':None,'tag':'','bounds':None,'collision_channels':[]})['returnValue']
    if pps: pp=pps[0]
    else:
        pp=call(ST+'add_to_scene_from_class',{'actor_type':{'refPath':'/Script/Engine.PostProcessVolume'},'name':'BW_PostProcess','xform':{'location':{'x':23000,'y':31000,'z':500},'rotation':{'pitch':0,'yaw':0,'roll':0},'scale':{'x':1,'y':1,'z':1}}})['returnValue']
        call(ST+'set_actor_folder',{'actor':pp,'folder_path':'Sky'})
    setp(pp,{'bUnbound':True,'bIsSpatiallyLoaded':False},'pp')
    S={'bOverride_BloomIntensity':True,'bloomIntensity':0.9,'bOverride_AutoExposureBias':True,'autoExposureBias':__EXPO__,'bOverride_VignetteIntensity':True,'vignetteIntensity':0.3,
       'bOverride_ColorSaturation':True,'colorSaturation':{'x':1.12,'y':1.12,'z':1.12,'w':1.0},'bOverride_ColorContrast':True,'colorContrast':{'x':1.06,'y':1.06,'z':1.06,'w':1.0},
       'bOverride_LensFlareIntensity':True,'lensFlareIntensity':0.45,'bOverride_AmbientOcclusionIntensity':True,'ambientOcclusionIntensity':0.6,
       'bOverride_LocalExposureHighlightContrastScale':True,'localExposureHighlightContrastScale':0.72,'bOverride_LocalExposureShadowContrastScale':True,'localExposureShadowContrastScale':0.85,
       'bOverride_AutoExposureMinBrightness':False,'bOverride_AutoExposureMaxBrightness':False}
    try: call(OT+'set_properties',{'instance':pp,'values':json.dumps({'settings':S})})
    except Exception as e: out['err'].append('pp settings '+str(e)[:300])
    try: out['pp']=str(call(OT+'get_properties',{'instance':pp,'properties':['bUnbound','settings']})['returnValue'])[:200]
    except Exception as e: out['pp']=str(e)[:150]
    return out
