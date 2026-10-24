Scriptname CT_SkyPrompt extends Quest
; Optional SkyPrompt mode (CarryThem - SkyPrompt.esp): a "Carry" prompt on the NPC in the crosshair, and
; "Set down" while carrying. Accepting it does what the power does (CT_Control.Toggle / Drop).
; Without SkyPrompt it stays off (SKSE.GetPluginVersion guard), as RSE does.

Import SkyPrompt

CT_Control Property Control Auto
Keyword Property ActorTypeNPC Auto
GlobalVariable Property KeyboardKey Auto ; DirectX scan code, CT_PromptKey (default G)
GlobalVariable Property GamepadKey Auto ; SkyPrompt gamepad code, CT_PromptGamepadKey (default 278: X / Square)
GlobalVariable Property Enabled Auto ; CT_PromptEnabled in CarryThem.esp (MCM toggle): 0 = no prompt
string Property CarryText = "Carry" Auto ; set by the plugin, French in the French one
string Property DropText = "Set down" Auto
int Property CarryEvent = 1 AutoReadOnly
int Property DropEvent = 2 AutoReadOnly
float Property HoldTime = 1.0 AutoReadOnly
float Property HideDelay = 0.3 AutoReadOnly ; the crosshair often leaves the NPC for an instant

int clientID ; 0 = not registered
int shown ; event of the prompt on screen, 0 = none
Actor shownFor ; who that prompt is about (None for "Set down")
Actor target

Event OnInit()
	Init()
EndEvent

; Also called by the player alias on each load: SkyPrompt gives out a new client ID every session.
Function Init()
	clientID = 0
	shown = 0
	shownFor = None
	if SKSE.GetPluginVersion("SkyPrompt") >= 0
		clientID = RegisterForSkyPromptEvent(self)
	endif
	if clientID > 0
		RegisterForCrosshairRef()
		; The prompt stayed on screen during conversations: hide it while a menu is open.
		RegisterForMenu("Dialogue Menu")
		RegisterForMenu("MessageBoxMenu")
		RegisterForModEvent("CarryThem_Changed", "OnCarryChanged") ; sent by CT_Control when a carry starts or ends
	else
		UnregisterForCrosshairRef()
		Debug.Trace("[CarryThem] SkyPrompt not found or refused the registration: no prompt")
	endif
EndFunction

Event OnCrosshairRefChange(ObjectReference ref)
	Refresh(ref as Actor)
EndEvent

Event OnMenuOpen(string asMenuName)
	Hide()
EndEvent

Event OnMenuClose(string asMenuName)
	Refresh(Game.GetCurrentCrosshairRef() as Actor)
EndEvent

; Without it, "Set down" only showed once the crosshair moved after the pick-up.
Event OnCarryChanged(string asEventName, string asArg, float afArg, Form akSender)
	Refresh(Game.GetCurrentCrosshairRef() as Actor)
EndEvent

Event OnUpdate()
	Refresh(Game.GetCurrentCrosshairRef() as Actor, true)
EndEvent

; Shows the prompt that fits what the player looks at. abNow: hide at once instead of after HideDelay.
Function Refresh(Actor akCandidate, bool abNow = false)
	if clientID <= 0
		return
	elseif Enabled.GetValueInt() == 0 || UI.IsMenuOpen("Dialogue Menu") || UI.IsMenuOpen("MessageBoxMenu")
		Hide()
	elseif Control.Passenger.GetActorRef()
		Show(DropText, DropEvent, None)
	elseif akCandidate && akCandidate.HasKeyword(ActorTypeNPC) && !akCandidate.IsDead() && !akCandidate.IsHostileToActor(Game.GetPlayer())
		target = akCandidate
		Show(CarryText, CarryEvent, akCandidate)
	elseif abNow
		Hide()
	elseif shown
		RegisterForSingleUpdate(HideDelay) ; hide only if the crosshair is still elsewhere then (no flicker)
	endif
EndFunction

Function Show(string asText, int aiEvent, Actor akFor)
	if shown == aiEvent && shownFor == akFor
		return ; already on screen: sending it again made it flicker
	endif
	Hide()
	int[] devices = new int[2]
	int[] keys = new int[2]
	devices[0] = 0 ; keyboard
	devices[1] = 2 ; gamepad
	keys[0] = KeyboardKey.GetValueInt()
	keys[1] = GamepadKey.GetValueInt()
	shown = aiEvent
	shownFor = akFor
	SendPrompt(clientID, asText, aiEvent, 0, 1, None, devices, keys, HoldTime) ; type 1: hold
EndFunction

Function Hide()
	if shown
		RemovePrompt(clientID, shown, 0)
		shown = 0
		shownFor = None
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
