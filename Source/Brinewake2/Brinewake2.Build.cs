// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class Brinewake2 : ModuleRules
{
	public Brinewake2(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"Brinewake2",
			"Brinewake2/Variant_Horror",
			"Brinewake2/Variant_Horror/UI",
			"Brinewake2/Variant_Shooter",
			"Brinewake2/Variant_Shooter/AI",
			"Brinewake2/Variant_Shooter/UI",
			"Brinewake2/Variant_Shooter/Weapons"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
