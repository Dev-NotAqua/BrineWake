import json
AS='editor_toolset.toolsets.asset.AssetTools.'
F='/Game/Brinewake/Characters/'
def call(n,a): return execute_tool(n,json.dumps(a))
def names(folder): return [(a.get('packageName','') if isinstance(a,dict) else str(a)).split('/')[-1] for a in call(AS+'find_assets',{'folder_path':folder,'name':'','asset_type':'','recursive':False,'tags':{}})['returnValue']]
def run():
    out={'moved':0,'err':[]}
    try: call(AS+'create_folder',{'path':F+'Anims'})
    except Exception as e: pass
    pre='SK_BW_NPC_Alekeeper_Anim_BW_Rig_'
    for n in names(F[:-1]):
        if n.startswith(pre):
            try:
                call(AS+'move',{'path':F+n,'new_path':F+'Anims/'+n[len(pre):]}); out['moved']+=1
            except Exception as e: out['err'].append(n+' '+str(e)[:150])
    try: call(AS+'move',{'path':F+'SK_BW_NPC_Alekeeper_Skeleton','new_path':F+'SKEL_BW_Pirate'})
    except Exception as e: out['err'].append(str(e)[:150])
    out['anims']=len(names(F+'Anims'))
    out['root']=names(F[:-1])
    try: call(AS+'save_assets',{'asset_paths':[F+'Anims/'+n for n in names(F+'Anims')]+[F+n for n in names(F[:-1])]})
    except Exception as e: out['err'].append('save '+str(e)[:150])
    return out
