// Copyright Epic Games, Inc. All Rights Reserved.

#include "EditorDiscordRichPresence.h"
#include "discord-files/discord.h"
#include "Runtime/Launch/Resources/Version.h"
#include "Runtime/Core/Public/Misc/App.h"
#if WITH_EDITOR
#include "UnrealEd.h"
#include "Subsystems/AssetEditorSubsystem.h"
//#include "Toolkits/AssetEditorToolkit.h"
//#include "AssetEditorSubsystem.h"
#include "Interfaces/IPluginManager.h"
#include "Framework/Application/SlateApplication.h"
#endif
//#include "Editor/StaticMeshEditor/Public/StaticMeshEditorModule.h"
//#include "Editor/EditorFramework/Public/Tools/Modes.h"
#include "Editor/EditorFramework/Public/EditorModes.h"
#include "EditorModeManager.h"
#include "SlateBasics.h"
#include "SlateExtras.h"
#include "Editor/LevelEditor/Public/LevelEditor.h"
#include "Modules/ModuleManager.h"


#define LOCTEXT_NAMESPACE "FEditorDiscordRichPresenceModule"

discord::Core* fcore{};

void FEditorDiscordRichPresenceModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module
	// Get the base directory of this plugin
#if WITH_EDITOR
	//new
	UAssetEditorSubsystem* AssetSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
	if (AssetSubsystem)
	{
		AssetSubsystem->OnAssetEditorRequestedOpen().AddRaw(this, &FEditorDiscordRichPresenceModule::NotifyAssetOpened);
	}

	//ULevelEditorSubsystem* LevelSubsystem = GEditor->GetLevelEd

/*
	IStaticMeshEditorModule* StaticMeshEditorModule = &FModuleManager::LoadModuleChecked<IStaticMeshEditorModule>("StaticMeshEditor");
	{
		FAssetEditorManager::Get().OnAssetOpenedInEditor().AddRaw(this, &FEditorDiscordRichPresenceModule::NotifyAssetOpened);
	}*/

	//old
	FString BaseDir = IPluginManager::Get().FindPlugin("EditorDiscordRichPresence")->GetBaseDir();

	// Add on the relative location of the third party dll and load it
	FString LibraryPath;
#if PLATFORM_WINDOWS
	LibraryPath = FPaths::Combine(*BaseDir, TEXT("ThirdParty/Discord/x64/Release/discord_game_sdk.dll"));
	DLLHandle = FPlatformProcess::GetDllHandle(*LibraryPath);
#endif // PLATFORM_WINDOWS

#endif

	/*
	Grab that Client ID from earlier
	Discord.CreateFlags.Default will require Discord to be running for the game to work
	If Discord is not running, it will:
	1. Close your game
	2. Open Discord
	3. Attempt to re-open your game
	Step 3 will fail when running directly from the Unreal Engine editor
	Therefore, always keep Discord running during tests, or use Discord.CreateFlags.NoRequireDiscord*/

		auto result = discord::Core::Create(1023921525285457950, DiscordCreateFlags_NoRequireDiscord, &fcore);
		//discord::Activity activity{};
		activity.SetType(discord::ActivityType::Playing);


		//Get project name from project settings, if blank get it from FApp (module name?)
		//FString ProjectName;

		//get project name from project config
		GConfig->GetString(
			TEXT("/Script/EngineSettings.GeneralProjectSettings"),
			TEXT("ProjectName"),
			ProjectName,
			GGameIni
		);

		//check if its blank and use FApp to get it
		if (ProjectName.IsEmpty())
		{
			ProjectName = FApp::GetProjectName();

			if (ProjectName.IsEmpty())
			{
				ProjectName = "Untitled Project";
			}
		}

		//get engine version
		//FString VersionNum = "Engine Version: ";
		VersionNum.AppendInt(ENGINE_MAJOR_VERSION);
		VersionNum.Append(".").AppendInt(ENGINE_MINOR_VERSION);
		VersionNum.Append(".").AppendInt(ENGINE_PATCH_VERSION);


		//combine with engine ver
		ProjectName.Append(" | ");
		ProjectName.Append(VersionNum);

		//ini status
		EditorStatus = "Level";

		activity.SetDetails(TCHAR_TO_ANSI(*ProjectName));
		activity.SetState(TCHAR_TO_ANSI(*EditorStatus));

		discord::Timestamp time = FDateTime::UtcNow().ToUnixTimestamp();
		activity.GetTimestamps().SetStart(time);

		activity.GetAssets().SetLargeImage("ue5");

		if (fcore)
		{
			fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});
		}
		else
		{
			UE_LOG(LogTemp, Log, TEXT("Discord Error: fcore is null"));
		}


		//Tick for Discord update
		TickDelegate = FTickerDelegate::CreateRaw(this, &FEditorDiscordRichPresenceModule::Tick);
		//TickDelegateHandle = FTicker::GetCoreTicker().AddTicker(TickDelegate);
		TickDelegateHandle = FTSTicker::GetCoreTicker().AddTicker(TickDelegate);

		//FSlateApplication* SApp = &FSlateApplication::Get();
		//FText WTitle = SApp->GetActiveTopLevelRegularWindow()->GetTitle();
	
		FSlateApplication::Get().OnApplicationActivationStateChanged().AddRaw(
			this, &FEditorDiscordRichPresenceModule::OnWindowFocusChanged
		);
		
		//if (SApp)
		//{
			//FString WTitle = SApp->GetTitle().ToString();

			//UE_LOG(LogTemp, Log, TEXT("ProjectName: %s"), *WTitle);
		//}
		//else
		//{
			//UE_LOG(LogTemp, Log, TEXT("ProjectName: NULL"));
		//}


		//del tests
		FEditorDelegates::BeginPIE.AddRaw(this, &FEditorDiscordRichPresenceModule::PlayInEditorBegin);
		FEditorDelegates::EndPIE.AddRaw(this, &FEditorDiscordRichPresenceModule::PlayInEditorEnd);
		//FEditorDelegates::selec.AddRaw(this, &FEditorDiscordRichPresenceModule::EditorModeIDExit);

		//FName ModName = TEXT("LevelEditor");
		FLevelEditorModule& levelEditor = FModuleManager::GetModuleChecked<FLevelEditorModule>(TEXT("LevelEditor"));
		levelEditor.OnActorSelectionChanged().AddRaw(this, &FEditorDiscordRichPresenceModule::OnSelectionChanged);


		//FEditorDelegates::EditorModeIDEnter.AddRaw(this, &FEditorDiscordRichPresenceModule::EditorModeIDExit);
		//AssetSubsystem->OnEditorModeRegistered().AddRaw(this,&FEditorDiscordRichPresenceModule::EditorModeIDExit);
/*
		FEditorModeInfo ModeInfo;
		AssetSubsystem->FindEditorModeInfo(FBuiltinEditorModes::EM_Level, ModeInfo);
		ModeInfo.*/
}

void FEditorDiscordRichPresenceModule::OnWindowFocusChanged(bool bIsFocused)
{
    bHasFocus = bIsFocused;

    // Keep presence alive when alt-tabbing to Discord to check it.
    if (fcore)
    {
        fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});
    }
}

void FEditorDiscordRichPresenceModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
#if WITH_EDITOR
	//FTicker::GetCoreTicker().RemoveTicker(TickDelegateHandle);
	FTSTicker::GetCoreTicker().RemoveTicker(TickDelegateHandle);
	FPlatformProcess::FreeDllHandle(DLLHandle);
	
	if (FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().OnApplicationActivationStateChanged().RemoveAll(this);
	}

	DestroyDiscordCore();
#endif
}

bool FEditorDiscordRichPresenceModule::Tick(float DeltaTime)
{
	//FEditorDiscordRichPresenceModule::Update(DeltaTime);
	//UpdateFocusedWindowStatus();
	UpdateDiscordStatus();





	FSlateApplication* SApp = &FSlateApplication::Get();
	if (SApp)
	{
		//FText WTitle = SApp->GetActiveTopLevelRegularWindow()->;
		//UE_LOG(LogTemp, Log, TEXT("ProjectName: %s"), *WTitle.ToString());
	}

	if (::fcore)
	{
		::fcore->RunCallbacks();
	}


	return true;
}


void FEditorDiscordRichPresenceModule::UpdateFocusedWindowStatus()
{
	//FAssetEditorManager assetEditorManager = FAssetEditorManager::Get();
	//TArray<UObject*> editedAssets = assetEditorManager.GetAllEditedAssets();
	//TArray<IAssetEditorInstance*> openedEditors
	//IAssetEditorInstance* focusedEditor = nullptr;


	UAssetEditorSubsystem* AssetSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
	if (AssetSubsystem)
	{
		TArray<UObject*> editedAssets = AssetSubsystem->GetAllEditedAssets();
		TArray<IAssetEditorInstance*> openedEditors;

		for (UObject* editedAsset : editedAssets)
		{
			if (editedAsset)
			{
				openedEditors.Add(AssetSubsystem->FindEditorForAsset(editedAsset, false));
			}

		}

		double maxLastActivationTime = 0.0;

		for (IAssetEditorInstance* openedEditor : openedEditors)
		{
			if (openedEditor && openedEditor->GetLastActivationTime() > maxLastActivationTime)
			{
				maxLastActivationTime = openedEditor->GetLastActivationTime();
				FocusedEditor = openedEditor;

				//UE_LOG(LogTemp, Log, TEXT("Discord: %f"), maxLastActivationTime);
			}
		}



		if (!FocusedEditor)
		{
			EditorStatus = "Level";
			activity.SetState(TCHAR_TO_ANSI(*EditorStatus));
			activity.GetAssets().SetLargeImage("editor");

			//UE_LOG(LogTemp, Log, TEXT("Discord: %s"), *EditorStatus);
		}
		else if (FocusedEditor)
		{

			FString AssetNameWithType = GetAssetNameForEditor(FocusedEditor);
			if (!AssetNameWithType.IsEmpty())
			{
				EditorStatus = AssetNameWithType;
			}
			else
			{
				EditorStatus = GetFriendlyEditorName(FocusedEditor->GetEditorName());
			}
			activity.GetAssets().SetLargeImage(TCHAR_TO_ANSI(*GetImageKey(FocusedEditor->GetEditorName())));
			activity.SetState(TCHAR_TO_ANSI(*EditorStatus));


			//UE_LOG(LogTemp, Log, TEXT("Discord: %s"), *EditorStatus);
		}
		else/* if(FocusedEditor && !GLevelEditorModeTools().IsModeActive(FBuiltinEditorModes::EM_Level))*/
		{
			FEditorModeID EID = FBuiltinEditorModes::EM_Level;



			if (GLevelEditorModeTools().IsOnlyVisibleActiveMode(FBuiltinEditorModes::EM_Default) && EditorStatus != "Level")
			{
				EditorStatus = "Level";
				activity.SetState(TCHAR_TO_ANSI(*EditorStatus));/**/
			}
		}

		//clear
		FocusedEditor = nullptr;
		//UE_LOG(LogTemp, Log, TEXT("Discord: %s"), *EditorStatus);
		//update
		if (fcore)
		{
			fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});
		}
	}
}


void FEditorDiscordRichPresenceModule::UpdateDiscordStatus()
{
    if (bIsInPIE)
    {
        EditorStatus = "Playing In Editor";
        activity.SetState(TCHAR_TO_ANSI(*EditorStatus));
        if (fcore)
            fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});
        return;
    }

    UAssetEditorSubsystem* AssetSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
    if (!AssetSubsystem) return;

    TArray<UObject*> editedAssets = AssetSubsystem->GetAllEditedAssets();

    // Find the most recently activated asset editor (excluding level editor)
    IAssetEditorInstance* MostRecentEditor = nullptr;
    double MostRecentTime = 0.0;

    for (UObject* editedAsset : editedAssets)
    {
        if (!editedAsset) continue;
        IAssetEditorInstance* Editor = AssetSubsystem->FindEditorForAsset(editedAsset, false);
        if (!Editor) continue;
        if (Editor->GetEditorName() == FName("LevelEditor")) continue;

        if (Editor->GetLastActivationTime() > MostRecentTime)
        {
            MostRecentTime = Editor->GetLastActivationTime();
            MostRecentEditor = Editor;
        }
    }

	// Get level editor activation time via the level editor module directly
	double LevelEditorTime = 0.0;
	FLevelEditorModule* LevelEditorModule = FModuleManager::GetModulePtr<FLevelEditorModule>("LevelEditor");
	if (LevelEditorModule)
	{
		TSharedPtr<ILevelEditor> LevelEditor = LevelEditorModule->GetFirstLevelEditor();
		if (LevelEditor.IsValid())
		{
			TSharedPtr<SWindow> LevelEditorWindow = FSlateApplication::Get().FindWidgetWindow(LevelEditor->AsShared());
			if (LevelEditorWindow.IsValid() && FSlateApplication::Get().GetActiveTopLevelRegularWindow() == LevelEditorWindow)
			{
				// Level editor window is the active window, give it a very high time
				LevelEditorTime = FPlatformTime::Seconds();
			}
		}
	}

    // Whichever was activated most recently wins
    if (MostRecentEditor && MostRecentTime > LevelEditorTime)
    {
        FString AssetNameWithType = GetAssetNameForEditor(MostRecentEditor);
        EditorStatus = AssetNameWithType.IsEmpty()
            ? GetFriendlyEditorName(MostRecentEditor->GetEditorName())
            : AssetNameWithType;
        activity.GetAssets().SetLargeImage(TCHAR_TO_ANSI(*GetImageKey(MostRecentEditor->GetEditorName())));
    }
    else
    {
        FString LevelName = GetCurrentLevelName();
        EditorStatus = LevelName.IsEmpty() ? FString("Level") : FString(TEXT("Level - ")) + LevelName;
        activity.GetAssets().SetLargeImage("editor");
    }

    activity.SetState(TCHAR_TO_ANSI(*EditorStatus));
    if (fcore)
        fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});

    FocusedEditor = nullptr;
}
void FEditorDiscordRichPresenceModule::NotifyAssetOpened(UObject* Asset/*, IAssetEditorInstance* InInstance*/)
{
	//UE_LOG(LogTemp, Warning, TEXT("Discord Asset opened"));
}

FString FEditorDiscordRichPresenceModule::GetAssetNameForEditor(IAssetEditorInstance* Editor)
{
	if (!Editor)
	{
		return FString();
	}

	// Check if we're in the level editor
	if (Editor->GetEditorName() == FName("LevelEditor"))
	{
		FString LevelName = GetCurrentLevelName();
		if (!LevelName.IsEmpty())
		{
			return TEXT("Level") + FString(TEXT(" - ")) + LevelName;
		}
		return TEXT("Level");
	}

	UAssetEditorSubsystem* AssetSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
	if (!AssetSubsystem)
	{
		return FString();
	}

	TArray<UObject*> EditedAssets = AssetSubsystem->GetAllEditedAssets();
	for (UObject* Asset : EditedAssets)
	{
		if (!Asset)
		{
			continue;
		}

		IAssetEditorInstance* AssetEditor = AssetSubsystem->FindEditorForAsset(Asset, false);
		if (AssetEditor == Editor)
		{
			FString AssetType = GetAssetTypeDisplayName(Asset);
			FString AssetName = Asset->GetName();
			
			if (!AssetType.IsEmpty())
			{
				return AssetType + FString(TEXT(" - ")) + AssetName;
			}
			return AssetName;
		}
	}

	return FString();
}

FString FEditorDiscordRichPresenceModule::GetFriendlyEditorName(FName EditorName)
{
	FString FriendlyName = FName::NameToDisplayString(EditorName.ToString(), false);
	FriendlyName.RemoveFromEnd(TEXT(" Editor"));
	return FriendlyName;
}

FString FEditorDiscordRichPresenceModule::GetAssetTypeDisplayName(UObject* Asset)
{
	if (!Asset)
	{
		return FString();
	}

	UClass* AssetClass = Asset->GetClass();
	if (!AssetClass)
	{
		return FString();
	}

	FString ClassName = AssetClass->GetName();

	// Map common asset class names to friendly display names
	if (ClassName == TEXT("Blueprint_GeneratedClass") || ClassName == TEXT("BlueprintGeneratedClass"))
	{
		return TEXT("Blueprint");
	}
	else if (ClassName == TEXT("WidgetBlueprintGeneratedClass"))
	{
		return TEXT("Widget");
	}
	else if (ClassName == TEXT("AnimBlueprint"))
	{
		return TEXT("Animation");
	}
	else if (ClassName == TEXT("SkeletalMesh"))
	{
		return TEXT("Skeletal Mesh");
	}
	else if (ClassName == TEXT("StaticMesh"))
	{
		return TEXT("Static Mesh");
	}
	else if (ClassName == TEXT("Texture2D"))
	{
		return TEXT("Texture");
	}
	else if (ClassName == TEXT("Material"))
	{
		return TEXT("Material");
	}
	else if (ClassName == TEXT("MaterialFunction"))
	{
		return TEXT("Material Function");
	}
	else if (ClassName == TEXT("MaterialParameterCollection"))
	{
		return TEXT("Material Parameters");
	}
	else if (ClassName == TEXT("Skeleton"))
	{
		return TEXT("Skeleton");
	}
	else if (ClassName == TEXT("PhysicsAsset"))
	{
		return TEXT("Physics Asset");
	}
	else if (ClassName == TEXT("AnimMontage"))
	{
		return TEXT("Montage");
	}
	else if (ClassName == TEXT("AnimSequence"))
	{
		return TEXT("Animation Sequence");
	}
	else if (ClassName == TEXT("SoundCue"))
	{
		return TEXT("Sound Cue");
	}
	else if (ClassName == TEXT("SoundWave"))
	{
		return TEXT("Sound Wave");
	}
	else if (ClassName == TEXT("SoundClass"))
	{
		return TEXT("Sound Class");
	}
	else if (ClassName == TEXT("SoundSubmix"))
	{
		return TEXT("Sound Submix");
	}
	else if (ClassName == TEXT("Particle"))
	{
		return TEXT("Particle");
	}
	else if (ClassName == TEXT("NiagaraSystem"))
	{
		return TEXT("Niagara System");
	}
	else if (ClassName == TEXT("NiagaraEmitter"))
	{
		return TEXT("Niagara Emitter");
	}
	else if (ClassName == TEXT("DataTable"))
	{
		return TEXT("Data Table");
	}
	else if (ClassName == TEXT("CurveTable"))
	{
		return TEXT("Curve Table");
	}
	else if (ClassName == TEXT("Curve"))
	{
		return TEXT("Curve");
	}
	else if (ClassName == TEXT("LevelSequence"))
	{
		return TEXT("Sequence");
	}
	else if (ClassName == TEXT("MetaHuman"))
	{
		return TEXT("MetaHuman");
	}
	else if (ClassName == TEXT("Enum"))
	{
		return TEXT("Enum");
	}
	else if (ClassName == TEXT("Structure"))
	{
		return TEXT("Structure");
	}
	else if (ClassName == TEXT("Dialogue"))
	{
		return TEXT("Dialogue");
	}
	else if (ClassName == TEXT("DialogueVoice"))
	{
		return TEXT("Dialogue Voice");
	}
	else if (ClassName == TEXT("Converter") || ClassName == TEXT("AssetActionUtility"))
	{
		return TEXT("Utility");
	}
	else if (ClassName == TEXT("DM_DataModel"))
	{
		return TEXT("Data Model");
	}
	else if (ClassName.Contains(TEXT("Blueprint")))
	{
		return TEXT("Blueprint");
	}

	// Remove trailing 'Class' if present and return as-is
	if (ClassName.EndsWith(TEXT("Class")))
	{
		ClassName.RemoveFromEnd(TEXT("Class"));
	}

	return ClassName;
}

FString FEditorDiscordRichPresenceModule::GetCurrentLevelName()
{
	UWorld* EditorWorld = GEditor->GetEditorWorldContext().World();
	if (!EditorWorld)
	{
		return FString();
	}

	FString MapName = EditorWorld->GetMapName();
	if (MapName.IsEmpty())
	{
		return FString();
	}

	// Extract just the map filename without the path
	// MapName is typically "/Game/Maps/MyLevel"
	if (MapName.StartsWith(TEXT("/Game/")))
	{
		MapName.RemoveFromStart(TEXT("/Game/Maps/"));
		if (!MapName.Contains(TEXT("/")))
		{
			return MapName;
		}
		// If still contains path, take the last part
		int32 LastSlash = MapName.Find(TEXT("/"), ESearchCase::IgnoreCase, ESearchDir::FromEnd);
		if (LastSlash != INDEX_NONE)
		{
			return MapName.Mid(LastSlash + 1);
		}
	}

	return MapName;
}

void FEditorDiscordRichPresenceModule::PlayInEditorBegin(bool bIsSimulating)
{
	PrePIEStatus = EditorStatus;
	//bIsLevelEditor = false;
	bIsInPIE = true;
	//UE_LOG(LogTemp, Warning, TEXT("Discord BeginPIE"));
}

void FEditorDiscordRichPresenceModule::PlayInEditorEnd(bool bIsSimulating)
{
	//bIsLevelEditor = true;
	bIsInPIE = false;
	//UE_LOG(LogTemp, Warning, TEXT("Discord EndPIE"));
}

void FEditorDiscordRichPresenceModule::OnSelectionChanged(const TArray<UObject*>& Selection, bool MyBool)
{
	//LastActiveTime += 1;
	bIsLevelEditor = true;
	//UE_LOG(LogTemp, Warning, TEXT("Discord Selection changed"));
}

FString FEditorDiscordRichPresenceModule::GetImageKey(FName EditorName)
{
	FString KeyResult = "default";

	//blueprint
	if (EditorName == FName("BlueprintEditor"))
	{
		KeyResult = "bp";
	}
	else if (EditorName == FName("AnimBlueprint") || EditorName == FName("AnimBlueprintEditor"))
	{
		KeyResult = "anim";
	}
	else if (EditorName == FName("WidgetBlueprintEditor"))
	{
		KeyResult = "ui";
	}
	else if (EditorName == FName("StaticMeshEditor"))
	{
		KeyResult = "mesh";
	}
	else if (EditorName == FName("SkeletalMeshEditor"))
	{
		KeyResult = "mesh";
	}
	else if (EditorName == FName("TextureEditor"))
	{
		KeyResult = "texture";
	}
	else if (EditorName == FName("MaterialEditor") || EditorName == FName("MaterialInstanceEditor"))
	{
		KeyResult = "mat";
	}
	else if (EditorName == FName("MaterialFunctionEditor"))
	{
		KeyResult = "mat";
	}
	else if (EditorName == FName("EnumEditor"))
	{
		KeyResult = "bp";
	}
	else if (EditorName == FName("SoundCueEditor") || EditorName == FName("SoundSubmixEditor") || EditorName == FName("SoundClassEditor"))
	{
		KeyResult = "sound";
	}
	else if (EditorName == FName("SoundWaveEditor"))
	{
		KeyResult = "sound";
	}
	else if (EditorName == FName("DataTableEditor") || EditorName == FName("CurveTableEditor"))
	{
		KeyResult = "data";
	}
	else if (EditorName == FName("CurveEditor"))
	{
		KeyResult = "curve";
	}
	else if (EditorName == FName("SequenceRecorderEditor") || EditorName == FName("LevelSequenceEditor"))
	{
		KeyResult = "sequence";
	}
	else if (EditorName == FName("NiagaraSystemEditor") || EditorName == FName("NiagaraEmitterEditor"))
	{
		KeyResult = "niagara";
	}
	else if (EditorName == FName("GenericAssetEditor"))
	{
		KeyResult = "default";
	}
	else if (EditorName == FName("SpriteEditor"))
	{
		KeyResult = "sprite";
	}
	else if (EditorName == FName("LevelEditor"))
	{
		KeyResult = "editor";
	}

	//UE_LOG(LogTemp, Warning, TEXT("DiscordRP: Set to %s for %s"), *KeyResult, *EditorName.ToString());

	return KeyResult;
}

void FEditorDiscordRichPresenceModule::InitDiscordCore()
{
    discord::Core::Create(1023921525285457950, DiscordCreateFlags_NoRequireDiscord, &fcore);
    if (fcore)
    {
        fcore->ActivityManager().UpdateActivity(activity, [](discord::Result result) {});
    }
}

void FEditorDiscordRichPresenceModule::DestroyDiscordCore()
{
    if (fcore)
    {
        delete fcore;
        fcore = nullptr;
    }
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FEditorDiscordRichPresenceModule, EditorDiscordRichPresence)