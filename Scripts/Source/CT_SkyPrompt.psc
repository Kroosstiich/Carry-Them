Scriptname CT_SkyPrompt extends Quest
; Optional SkyPrompt mode (CarryThem - SkyPrompt.esp): a "Carry" prompt on the NPC in the crosshair, and
; "Set down" while carrying. Accepting it does what the power does (CT_Control.Toggle / Drop).
; Without SkyPrompt it stays off (SKSE.GetPluginVersion guard), as RSE does.

Import SkyPrompt

CT_Control Property Control Auto
Keyword Property ActorTypeNPC Auto
GlobalVariable Property KeyboardKey Auto ; DirectX scan code, CT_PromptKey (default G)
GlobalVariable Property GamepadKey Auto ; SkyPrompt gamepad code, CT_PromptGamepadKey (default 278: X / Square)
string Property CarryText = "Carry" Auto ; set by the plugin, French in the French one
string Property DropText = "Set down" Auto
int Property CarryEvent = 1 AutoReadOnly
int Property DropEvent = 2 AutoReadOnly
float Property HoldTime = 1.0 AutoReadOnly

int clientID ; 0 = not registered
int shown ; event of the prompt on screen, 0 = none
Actor target

Event OnInit()
	Init()
EndEvent

; Also called by the player alias on each load: SkyPrompt gives out a new client ID every session.
Function Init()
	clientID = 0
	shown = 0
	if SKSE.GetPluginVersion("SkyPrompt") >= 0
		clientID = RegisterForSkyPromptEvent(self)
	endif
	if clientID > 0
		RegisterForCrosshairRef()
	else
		UnregisterForCrosshairRef()
		Debug.Trace("[CarryThem] SkyPrompt not found or refused the registration: no prompt")
	endif
EndFunction

Event OnCrosshairRefChange(ObjectReference ref)
	if clientID <= 0
		return
	endif
	Actor candidate = ref as Actor
	if Control.Passenger.GetActorRef()
		Show(DropText, DropEvent)
	elseif candidate && candidate.HasKeyword(ActorTypeNPC) && !candidate.IsDead() && !candidate.IsHostileToActor(Game.GetPlayer())
		target = candidate
		Show(CarryText, CarryEvent)
	else
		Hide()
	endif
EndEvent

Function Show(string asText, int aiEvent)
	Hide()
	int[] devices = new int[2]
	int[] keys = new int[2]
	devices[0] = 0 ; keyboard
	devices[1] = 2 ; gamepad
	keys[0] = KeyboardKey.GetValueInt()
	keys[1] = GamepadKey.GetValueInt()
	shown = aiEvent
	SendPrompt(clientID, asText, aiEvent, 0, 1, None, devices, keys, HoldTime) ; type 1: hold
EndFunction

Function Hide()
	if shown
		RemovePrompt(clientID, shown, 0)
		shown = 0
	endif
EndFunction

Event OnSkyPromptEvent(Int aiClientID, Int eventType, Int eventID, Int actionID, float dx, float dy, float progress)
	if eventType != 0 ; accepted only (the API also sends declined, timeouts, key down / up...)
		return
	endif
	Hide()
	if eventID == DropEvent
		Control.Drop()
	elseif eventID == CarryEvent && target
		Control.Toggle(target)
	endif
EndEvent
