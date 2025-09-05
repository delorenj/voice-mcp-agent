#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::{CustomMenuItem, SystemTray, SystemTrayEvent, SystemTrayMenu, Manager};
use tauri_plugin_shell::process::CommandEvent;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use tokio::process::Command as TokioCommand;

struct AppState {
    stt_process: Mutex<Option<std::process::Child>>,
}

#[tauri::command]
async fn start_stt_daemon(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let mut process_guard = state.stt_process.lock().unwrap();
    
    if process_guard.is_some() {
        return Err("STT daemon is already running".to_string());
    }
    
    match Command::new("python3")
        .arg("system_stt_daemon.py")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(child) => {
            *process_guard = Some(child);
            Ok("STT daemon started successfully".to_string())
        }
        Err(e) => Err(format!("Failed to start STT daemon: {}", e)),
    }
}

#[tauri::command]
async fn stop_stt_daemon(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let mut process_guard = state.stt_process.lock().unwrap();
    
    if let Some(mut child) = process_guard.take() {
        match child.kill() {
            Ok(_) => Ok("STT daemon stopped successfully".to_string()),
            Err(e) => Err(format!("Failed to stop STT daemon: {}", e)),
        }
    } else {
        Err("STT daemon is not running".to_string())
    }
}

#[tauri::command]
async fn get_stt_status(state: tauri::State<'_, AppState>) -> Result<bool, String> {
    let process_guard = state.stt_process.lock().unwrap();
    Ok(process_guard.is_some())
}

fn main() {
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("start_stt".to_string(), "Start STT"))
        .add_item(CustomMenuItem::new("stop_stt".to_string(), "Stop STT"))
        .add_item(CustomMenuItem::new("show".to_string(), "Show"))
        .add_item(CustomMenuItem::new("quit".to_string(), "Quit"));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .system_tray(SystemTray::new().with_menu(tray_menu))
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => {
                let app_handle = app.app_handle();
                match id.as_str() {
                    "start_stt" => {
                        let state: tauri::State<AppState> = app_handle.state();
                        tauri::async_runtime::spawn(async move {
                            match start_stt_daemon(state).await {
                                Ok(msg) => {
                                    app_handle.tray_handle()
                                        .get_item("start_stt")
                                        .set_enabled(false)
                                        .unwrap();
                                    app_handle.tray_handle()
                                        .get_item("stop_stt")
                                        .set_enabled(true)
                                        .unwrap();
                                    app_handle.emit_all("stt_status", true).unwrap();
                                }
                                Err(e) => {
                                    println!("Error starting STT: {}", e);
                                }
                            }
                        });
                    }
                    "stop_stt" => {
                        let state: tauri::State<AppState> = app_handle.state();
                        taira::async_runtime::spawn(async move {
                            match stop_stt_daemon(state).await {
                                Ok(msg) => {
                                    app_handle.tray_handle()
                                        .get_item("start_stt")
                                        .set_enabled(true)
                                        .unwrap();
                                    app_handle.tray_handle()
                                        .get_item("stop_stt")
                                        .set_enabled(false)
                                        .unwrap();
                                    app_handle.emit_all("stt_status", false).unwrap();
                                }
                                Err(e) => {
                                    println!("Error stopping STT: {}", e);
                                }
                            }
                        });
                    }
                    "show" => {
                        let window = app_handle.get_window("main").unwrap();
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                    "quit" => {
                        let state: tauri::State<AppState> = app_handle.state();
                        let mut process_guard = state.stt_process.lock().unwrap();
                        if let Some(mut child) = process_guard.take() {
                            let _ = child.kill();
                        }
                        std::process::exit(0);
                    }
                    _ => {}
                }
            }
            _ => {}
        })
        .manage(AppState {
            stt_process: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_stt_daemon,
            stop_stt_daemon,
            get_stt_status
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}