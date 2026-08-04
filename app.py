import customtkinter as ctk

#set apprearance mode
ctk.set_appearance_mode("dark")

#set default color theme
ctk.set_default_color_theme("blue")

#Create main application window
app = ctk.CTk()

#set window title
app.title("MealTrack AI")

#set window size
app.geometry("600x400")

#start application
app.mainloop()