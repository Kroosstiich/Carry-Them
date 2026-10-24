Scriptname CT_MCM extends MCM_ConfigBase
; Carry Them's MCM. The whole menu is declared in MCM\Config\CarryThem\config.json (MCM Helper): its
; controls write the CT_Offset*, CT_Rotation, CT_Princess* and CT_Hotkey globals that CT_Control reads.

CT_Control Property Control Auto

Event OnConfigClose()
	Control.RegisterHotkey() ; the key may have changed
EndEvent
