import customtkinter as ctk
import tkinter.filedialog
import os
from customtkinter import CTkInputDialog
from send2trash import send2trash
from fuzzywuzzy import fuzz
import logging
import re

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Application Configuration ---
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"


# --- Main Application Class ---
class OrderlyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Orderly - by Project Curator")
        self.geometry("800x600")
        self.minsize(600, 450)

        # --- Internal State Variables ---
        self.selected_folder = None
        self.found_files_map = {}  # Maps filename to full path
        self.file_buttons = []  # List of CTkButton widgets for files
        self.selected_file_button = None  # Currently selected file button widget

        # --- Main Grid Configuration (rows 0, 1, 2, 3) ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Search controls
        self.grid_rowconfigure(1, weight=10)  # Results list (takes most space)
        self.grid_rowconfigure(2, weight=0)  # Action buttons
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # --- TOP FRAME: Search Controls (on main grid row 0) ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.search_frame.grid_columnconfigure(1, weight=1)  # Makes search entry expand
        self.search_frame.grid_columnconfigure(2, weight=0)  # For new Search button

        self.select_folder_button = ctk.CTkButton(self.search_frame, text="Select Folder",
                                                  command=self.select_folder_and_search)
        self.select_folder_button.grid(row=0, column=0, padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Enter keyword to search for...",
                                         text_color="gray")  # Default to gray for placeholder
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.trigger_search)  # Bind Enter key always
        self.search_entry.bind("<FocusIn>", self.clear_placeholder_on_focus)  # Clear placeholder on click
        self.search_entry.bind("<FocusOut>", self.restore_placeholder_on_focus_out)  # Restore placeholder on focus out

        # NEW: Dedicated Search Button
        self.search_button = ctk.CTkButton(self.search_frame, text="Search", command=self.trigger_search)
        self.search_button.grid(row=0, column=2, padx=10, pady=10)

        self.selected_folder_label = ctk.CTkLabel(self.search_frame, text="No folder selected.", text_color="gray",
                                                  anchor="w")
        self.selected_folder_label.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10),
                                        sticky="ew")  # columnspan 3 to span across new button

        # --- MIDDLE FRAME (inside search_frame): Search Options (on search_frame row 2) ---
        self.options_frame = ctk.CTkFrame(self.search_frame, fg_color="transparent")
        self.options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w")  # columnspan 3

        self.case_sensitive_var = ctk.BooleanVar(value=True)
        self.case_sensitive_check = ctk.CTkCheckBox(self.options_frame, text="Case Sensitive",
                                                    variable=self.case_sensitive_var,
                                                    command=self.update_search_options_state)
        self.case_sensitive_check.pack(side="left", padx=10)

        # CHANGE: Fuzzy Match from Checkbox to Switch
        self.fuzzy_match_var = ctk.BooleanVar(value=False)
        self.fuzzy_match_switch = ctk.CTkSwitch(
            self.options_frame,
            text="Fuzzy Match",
            variable=self.fuzzy_match_var,
            onvalue=True,
            offvalue=False,
            command=self.on_fuzzy_switch_toggle  # Calls the new fuzzy wrapper
        )
        self.fuzzy_match_switch.pack(side="left", padx=10)  # Adjusted padx

        self.search_mode_var = ctk.StringVar(value="Keyword")
        self.search_mode_switch = ctk.CTkSwitch(
            self.options_frame,
            text="Search by Extension",
            variable=self.search_mode_var,
            onvalue="Extension",
            offvalue="Keyword",
            command=self.on_extension_switch_toggle  # Calls the existing extension wrapper
        )
        self.search_mode_switch.pack(side="left", padx=20)

        # --- MAIN FRAME: Results List (on main grid row 1) ---
        self.results_frame = ctk.CTkFrame(self)
        self.results_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        self.results_list = ctk.CTkScrollableFrame(self.results_frame, label_text="Found Files")
        self.results_list.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- BOTTOM FRAME: Action Buttons (on main grid row 2) ---
        self.actions_frame = ctk.CTkFrame(self)
        self.actions_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.open_button = ctk.CTkButton(self.actions_frame, text="Open File", command=self.open_selected_file)
        self.open_button.pack(side="left", padx=10, pady=5)

        self.delete_button = ctk.CTkButton(self.actions_frame, text="Delete File", fg_color="#D32F2F",
                                           hover_color="#B71C1C", command=self.delete_selected_file)
        self.delete_button.pack(side="left", padx=10, pady=5)

        # --- STATUS BAR (on main grid row 3) ---
        self.status_bar = ctk.CTkLabel(self, text="Welcome to Orderly! Select a folder to begin.", anchor="w")
        self.status_bar.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")

        # --- Initial Setup Calls ---
        # Call update_search_options_state at the end of __init__
        # to ensure initial state of checkboxes (e.g., Case Sensitive enabled/disabled) is correct
        self.update_search_options_state()
        self.update_status("Welcome to Orderly! Select a folder to begin.")

    # --- Utility and UI Helper Functions ---
    def update_status(self, message, color="white"):
        """
        Updates the text and color of the status bar.
        Logs the message to console as INFO.
        Color can be 'white', 'green', or 'red'.
        """
        self.status_bar.configure(text=message)

        # Set text color based on status
        if color == "green":
            self.status_bar.configure(text_color=("#1B5E20", "#B2FF59"))  # Dark/Light green
            logging.info(f"UI Status (GREEN): {message}")
        elif color == "red":
            self.status_bar.configure(text_color=("#B71C1C", "#FF5252"))  # Dark/Light red
            logging.error(f"UI Status (RED): {message}")
        else:
            # Default text color (matches standard text)
            self.status_bar.configure(text_color=("black", "white"))
            logging.info(f"UI Status (WHITE): {message}")

    # Wrappers for switch toggles to clear results and update state
    def on_extension_switch_toggle(self):
        """Wrapper for 'Search by Extension' switch."""
        if self.search_mode_var.get() == "Extension":  # Just turned ON
            self.update_status("Extension search enabled. Enter a new query.", color="white")
            self.search_entry.configure(placeholder_text="Enter extension (e.g., .pdf, .docx)...", text_color="gray")
        else:  # Just turned OFF, reverting to Keyword
            self.update_status("Keyword search enabled. Enter a new query.", color="white")
            self.search_entry.configure(placeholder_text="Enter keyword to search for...", text_color="gray")

        self.search_entry.delete(0, "end")  # Clear current input when mode changes
        self.clear_results_and_selection()
        self.update_search_options_state()

    def on_fuzzy_switch_toggle(self):
        """Wrapper for 'Fuzzy Match' switch."""
        if self.fuzzy_match_var.get():  # Just turned ON
            self.update_status("Fuzzy Match enabled. Enter a new query.", color="white")
        else:  # Just turned OFF, reverting to non-fuzzy keyword search
            self.update_status("Fuzzy Match disabled. Enter a new query.", color="white")
            # If not in extension mode, default placeholder
            if self.search_mode_var.get() != "Extension":
                self.search_entry.configure(placeholder_text="Enter keyword to search for...", text_color="gray")

        self.search_entry.delete(0, "end")  # Clear current input
        self.clear_results_and_selection()
        self.update_search_options_state()

    def clear_results_and_selection(self):
        """Clears the results list and any current file selection."""
        for widget in self.results_list.winfo_children():
            widget.destroy()
        self.found_files_map = {}
        self.file_buttons = []
        self.selected_file_button = None

    def update_search_options_state(self):
        """
        Disables/enables the 'Case Sensitive' checkbox based on other options.
        """
        is_fuzzy_mode = self.fuzzy_match_var.get()
        is_extension_mode = (self.search_mode_var.get() == "Extension")

        if is_fuzzy_mode or is_extension_mode:
            # If fuzzy or extension search is on, force case-insensitivity
            self.case_sensitive_check.deselect()  # Ensure it's unchecked
            self.case_sensitive_check.configure(state="disabled")  # Disable it
        else:
            # Otherwise, re-enable the checkbox for normal keyword search
            self.case_sensitive_check.configure(state="normal")  # Re-enable it
            # We don't force it to be checked; the user's preference persists

    # Handle placeholder text behavior on focus
    def clear_placeholder_on_focus(self, event):
        """
        Clears the placeholder text when the user clicks into the search box,
        if the current text is still the placeholder. Sets text color to normal.
        """
        current_text = self.search_entry.get()
        placeholder_text = self.search_entry.cget("placeholder_text")
        if current_text == placeholder_text:
            self.search_entry.delete(0, "end")
            # Set text color to normal input color (usually white in dark mode, black in light mode)
            self.search_entry.configure(text_color=self.cget("text_color"))

    def restore_placeholder_on_focus_out(self, event):
        """
        Restores the placeholder text if the search entry is empty after losing focus.
        Sets text color back to gray.
        """
        if not self.search_entry.get():  # If entry is truly empty
            current_placeholder = self.search_entry.cget("placeholder_text")
            self.search_entry.configure(placeholder_text=current_placeholder, text_color="gray")

    # --- Core Application Logic Functions ---
    def select_folder_and_search(self):
        """
        Opens a dialog to select a folder, stores the path, updates the UI,
        and clears the search entry for fresh input.
        """
        folder_path = tkinter.filedialog.askdirectory(title="Select a Folder to Search")

        if not folder_path:
            self.selected_folder = None
            self.selected_folder_label.configure(text="No folder selected.", text_color="gray")
            self.update_status("Folder selection cancelled.", color="red")
            logging.info("Folder selection cancelled by user.")
            return

        self.selected_folder = folder_path
        self.selected_folder_label.configure(text=f"Searching in: {self.selected_folder}",
                                             text_color=("black", "white"))

        # Clear the search entry and restore placeholder state when a new folder is selected
        self.search_entry.delete(0, "end")
        self.restore_placeholder_on_focus_out(None)  # Call with None event to restore placeholder visual
        self.update_status(
            f"Selected folder: '{os.path.basename(self.selected_folder)}'. Enter keyword and press Enter to search.",
            color="green")
        logging.info(f"Folder selected: {self.selected_folder}")

    def trigger_search(self, event=None):
        """
        Gets the keyword, launches the search, and displays results as selectable buttons.
        Provides feedback via status bar and console.
        """
        if not self.selected_folder:
            self.update_status("Please select a folder before searching.", color="red")
            self.select_folder_and_search()  # Pro-actively open the dialog to guide user
            return

        keyword = self.search_entry.get().strip()  # Always strip whitespace from user input

        # Check if keyword is truly empty after stripping or if it's still the placeholder text
        if not keyword or (self.search_entry.cget("placeholder_text") != "" and keyword == self.search_entry.cget(
                "placeholder_text")):
            self.update_status("Search keyword is empty. Please enter a keyword.", color="red")
            return

        self.update_status(f"Searching for '{keyword}' in '{os.path.basename(self.selected_folder)}'...", color="white")
        self.results_list.update()  # Force UI update so status message is visible before potentially long search

        # Clear previous results and selections
        self.clear_results_and_selection()

        matching_files = self.perform_search(self.selected_folder, keyword)

        if not matching_files:
            self.update_status(f"No files found containing '{keyword}'.", color="red")
            label = ctk.CTkLabel(self.results_list, text="No matching files found.")
            label.pack(padx=10, pady=5, anchor="w")
        else:
            for file_path in matching_files:
                filename_only = os.path.basename(file_path)
                self.found_files_map[filename_only] = file_path

                file_button = ctk.CTkButton(self.results_list, text=filename_only, fg_color="transparent",
                                            text_color=("black", "white"), anchor="w")
                file_button.configure(command=lambda btn=file_button: self.select_file(btn))
                file_button.pack(fill="x", padx=5, pady=2)
                self.file_buttons.append(file_button)

            self.update_status(f"Search complete. Found {len(matching_files)} file(s).", color="green")
            logging.info(f"Search complete for '{keyword}'. Found {len(matching_files)} files.")

    def select_file(self, button_to_select):
        """
        Highlights the selected file button. Allows de-selecting by clicking again.
        """
        if self.selected_file_button == button_to_select:
            # If same button clicked, de-select it
            self.selected_file_button.configure(fg_color="transparent")
            self.selected_file_button = None
            self.update_status("File de-selected.")
            logging.info("File de-selected.")
            return

        # De-select the old button, if one was selected
        if self.selected_file_button:
            self.selected_file_button.configure(fg_color="transparent")

        # Select the new button
        button_to_select.configure(fg_color=("#3B8ED0", "#1F6AA5"))
        self.selected_file_button = button_to_select
        self.update_status(f"Selected: '{self.selected_file_button.cget('text')}'")
        logging.info(f"File selected: '{self.selected_file_button.cget('text')}'")

    def open_selected_file(self):
        """
        Opens the currently selected file using the default system application.
        Provides feedback via status bar and console.
        """
        if not self.selected_file_button:
            self.update_status("No file selected to open. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_open = self.found_files_map.get(selected_filename)

        if file_path_to_open and os.path.exists(file_path_to_open):
            self.update_status(f"Opening file: '{selected_filename}'...", color="green")
            logging.info(f"Opening file: {file_path_to_open}")
            os.startfile(file_path_to_open)
        else:
            self.update_status(f"Error: Could not find file path for '{selected_filename}'", color="red")
            logging.error(
                f"Error: File path not found or does not exist for '{selected_filename}' at '{file_path_to_open}'")

    def delete_selected_file(self):
        """
        Shows a robust confirmation dialog and then moves the selected file to the
        Recycle Bin, providing feedback via status bar and console.
        """
        if not self.selected_file_button:
            self.update_status("No file selected to delete. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_delete = self.found_files_map.get(selected_filename)

        if not file_path_to_delete or not os.path.exists(file_path_to_delete):
            self.update_status(f"Error: Could not find file path for '{selected_filename}'", color="red")
            logging.error(
                f"Error: File path not found or does not exist for '{selected_filename}' at '{file_path_to_delete}'")
            return

        dialog_text = (f"You are about to move this file to the Recycle Bin:\n\n"
                       f"'{file_path_to_delete}'\n\n"
                       f"To confirm, please type DELETE below and click OK.")

        dialog = CTkInputDialog(text=dialog_text, title="Confirm Deletion")
        user_input = dialog.get_input()

        if user_input and user_input.upper() == "DELETE":
            try:
                normalized_path = os.path.normpath(file_path_to_delete)
                send2trash(normalized_path)

                # Remove the file from the UI list and clear selection
                self.selected_file_button.destroy()
                self.selected_file_button = None

                self.update_status(f"Successfully moved '{selected_filename}' to the Recycle Bin.", color="green")
                logging.info(f"Successfully moved '{normalized_path}' to Recycle Bin.")

            except Exception as e:
                self.update_status(f"Error deleting file: {e}", color="red")
                logging.error(f"Error deleting file '{normalized_path}': {e}")
        else:
            self.update_status("Deletion cancelled by user.", color="white")
            logging.info("Deletion cancelled by user.")

    def perform_search(self, folder_path, keyword):
        """
        Searches for files based on the current search mode and options.
        Logs search parameters to console.
        """
        logging.info(f"Starting search in '{folder_path}' for '{keyword}' with mode='{self.search_mode_var.get()}', "
                     f"case_sensitive={self.case_sensitive_var.get()}, fuzzy_match={self.fuzzy_match_var.get()}")

        found_files = []

        mode = self.search_mode_var.get()
        is_case_sensitive = self.case_sensitive_var.get()
        is_fuzzy = self.fuzzy_match_var.get()

        # Prepare keyword for comparison based on case sensitivity setting
        keyword_for_comparison = keyword.lower() if not is_case_sensitive else keyword

        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                # Prepare filename for comparison based on case sensitivity setting
                target_text = filename.lower() if not is_case_sensitive else filename

                match_found = False
                if mode == "Extension":
                    # For extension search, strip non-alphanumeric chars from keyword (except dot),
                    # then clean any leading/trailing dots and ensure a single leading dot.
                    clean_ext = re.sub(r'[^\w.]', '', keyword_for_comparison).strip(
                        '.')  # Strip non-word chars and any leading/trailing dots

                    if clean_ext:  # Only add dot if there's an actual extension
                        clean_ext = '.' + clean_ext.lower()  # Ensure lowercase and add leading dot
                    else:  # If after cleaning, it's empty, no match can be found
                        continue

                        # Extension search should be exact by default
                    if target_text.lower().endswith(clean_ext):
                        match_found = True

                else:  # Keyword search (non-extension mode)
                    if is_fuzzy:
                        if fuzz.partial_ratio(keyword_for_comparison, target_text) > 75:  # Ratio 0-100
                            match_found = True
                    else:
                        if keyword_for_comparison in target_text:
                            match_found = True

                if match_found:
                    full_path = os.path.join(root, filename)
                    found_files.append(full_path)

        return found_files


# --- Run the Application ---
if __name__ == "__main__":
    app = OrderlyApp()
    app.mainloop()