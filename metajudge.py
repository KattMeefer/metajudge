#!/usr/bin/env python3
"""
Metajudge - A tool for reviewing and assessing judge evaluations of fitness insights.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, TclError
import pandas as pd
import os
import json
import hashlib
import platform
from datetime import datetime
from pathlib import Path
import tkinter.font as tkfont

def get_font(font_name, fallback='Helvetica'):
    """Checks if a font exists; returns it or a fallback."""
    try:
        tkfont.Font(family=font_name)
        return font_name
    except TclError:
        return fallback

def get_platform_fonts():
    """Defines preferred and fallback fonts for the current OS."""
    system = platform.system()
    
    if system == 'Darwin': # macOS
        default_font = get_font('SF Pro Display')
        mono_font = get_font('SF Mono', 'Courier')
    elif system == 'Windows':
        default_font = get_font('Segoe UI')
        mono_font = get_font('Consolas', 'Courier')
    else: # Linux and others
        default_font = 'Helvetica'
        mono_font = 'Courier'
        
    return {
        'default': (default_font, 10),
        'bold': (default_font, 10, 'bold'),
        'large': (default_font, 18, 'bold'),
        'medium': (default_font, 12, 'bold'),
        'small': (default_font, 9),
        'button': (default_font, 16, 'bold'),
        'mono': (mono_font, 10)
    }

class MetajudgeApp:
    def __init__(self, root):
        self.root = root
        
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        self.root.title("Metajudge - Judge Evaluation Review Tool")
        self.root.geometry("1200x800")
        
        self.FONTS = get_platform_fonts()
        
        self.insights_df = None
        self.workout_history_df = None
        self.current_insight_index = 0
        self.current_judge_index = 0
        
        # old school save method //self.save_directory = Path("metajudge_saves")
        self.save_directory = Path.home() / "Metajudge_Saves"


        self.save_directory.mkdir(exist_ok=True)
        self.current_save_file = None
        
        self.judge_categories = [
            'factuality', 'insightfulness', 'personalization',
            'actionability', 'safety', 'tone', 'toxicity'
        ]
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        logo_label = ttk.Label(main_frame, text="⚖️", font=(self.FONTS['large'][0], 32))
        logo_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        title_label = ttk.Label(main_frame, text="Metajudge - Judge Evaluation Review Tool",
                                font=self.FONTS['large'], foreground='#2c3e50')
        title_label.grid(row=1, column=0, columnspan=3, pady=(0, 25))
        
        import_frame = ttk.LabelFrame(main_frame, text="Data Import", padding="15")
        import_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        import_frame.columnconfigure(1, weight=1)
        
        ttk.Label(import_frame, text="Insights CSV:", font=self.FONTS['bold']).grid(row=0, column=0, sticky=tk.W, padx=(0, 15))
        self.insights_file_var = tk.StringVar()
        insights_entry = ttk.Entry(import_frame, textvariable=self.insights_file_var, state='readonly', font=self.FONTS['small'])
        insights_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 15))
        ttk.Button(import_frame, text="Browse...", command=self.browse_insights_file).grid(row=0, column=2)
        
        ttk.Label(import_frame, text="Workout History CSV:", font=self.FONTS['bold']).grid(row=1, column=0, sticky=tk.W, padx=(0, 15), pady=(15, 0))
        self.workout_file_var = tk.StringVar()
        workout_entry = ttk.Entry(import_frame, textvariable=self.workout_file_var, state='readonly', font=self.FONTS['small'])
        workout_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 15), pady=(15, 0))
        ttk.Button(import_frame, text="Browse...", command=self.browse_workout_file).grid(row=1, column=2, pady=(15, 0))
        
        button_frame = ttk.Frame(import_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(25, 0))
        
        start_style = ttk.Style()
        start_style.configure("GameButton.TButton", font=self.FONTS['button'], padding=(40, 20))
        
        self.load_review_btn = ttk.Button(button_frame, text="📂 LOAD LAST REVIEW", command=self.load_last_review,
                                          style="GameButton.TButton")
        self.load_review_btn.grid(row=0, column=0, padx=(0, 15))
        
        self.load_file_btn = ttk.Button(button_frame, text="📁 LOAD FILE", command=self.load_specific_file,
                                        style="GameButton.TButton")
        self.load_file_btn.grid(row=0, column=1, padx=(0, 15))
        
        self.start_review_btn = ttk.Button(button_frame, text="🚀 START NEW REVIEW", command=self.start_new_review,
                                           state='disabled', style="GameButton.TButton")
        self.start_review_btn.grid(row=0, column=2)
        
        self.update_load_button_state()
        
        preview_frame = ttk.LabelFrame(main_frame, text="Data Preview", padding="10")
        preview_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(preview_frame, show='headings', height=15)
        scrollbar_y = ttk.Scrollbar(preview_frame, orient='vertical', command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(preview_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready to import data...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief='sunken', anchor='w')
        status_label.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def browse_insights_file(self):
        filename = filedialog.askopenfilename(
            title="Select Insights CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.insights_file_var.set(filename)
            self.check_and_autoload()
            
    def browse_workout_file(self):
        filename = filedialog.askopenfilename(
            title="Select Workout History CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.workout_file_var.set(filename)
            self.check_and_autoload()
    
    def check_and_autoload(self):
        if self.insights_file_var.get() and self.workout_file_var.get():
            self.status_var.set("Auto-loading data...")
            self.load_data()
            
    def load_data(self, silent=False):
        insights_file = self.insights_file_var.get()
        workout_file = self.workout_file_var.get()
        
        if not insights_file:
            if not silent:
                messagebox.showerror("Error", "Please select an insights CSV file.")
            return False
            
        if not os.path.exists(insights_file):
            if not silent:
                messagebox.showerror("Error", f"Insights file not found: {insights_file}")
            return False
            
        try:
            self.insights_df = pd.read_csv(insights_file)
            insights_count = len(self.insights_df)
            
            required_columns = ['insight_text', 'email', 'goal']
            for category in self.judge_categories:
                required_columns.extend([f'{category}_score', f'{category}_reasoning'])
            
            missing_columns = [col for col in required_columns if col not in self.insights_df.columns]
            if missing_columns:
                messagebox.showwarning(
                    "Missing Columns", 
                    f"Warning: These expected columns are missing from insights:\n{', '.join(missing_columns)}\n\n"
                    f"Available columns:\n{', '.join(self.insights_df.columns.tolist())}"
                )
            
            if workout_file and os.path.exists(workout_file):
                self.workout_history_df = pd.read_csv(workout_file)
                workout_count = len(self.workout_history_df)
                
                required_workout_columns = ['email', 'workout_summary']
                missing_workout_columns = [col for col in required_workout_columns if col not in self.workout_history_df.columns]
                if missing_workout_columns:
                    messagebox.showwarning(
                        "Missing Workout Columns", 
                        f"Warning: These expected columns are missing from workout history:\n{', '.join(missing_workout_columns)}\n\n"
                        f"Available columns:\n{', '.join(self.workout_history_df.columns.tolist())}"
                    )
                
                if 'email' in self.insights_df.columns and 'email' in self.workout_history_df.columns:
                    insight_emails = set(self.insights_df['email'].dropna())
                    workout_emails = set(self.workout_history_df['email'].dropna())
                    matched_emails = insight_emails.intersection(workout_emails)
                    
                    status_msg = f"Loaded {insights_count} insights and {workout_count} workout histories. "
                    status_msg += f"Data linking: {len(matched_emails)}/{len(insight_emails)} insights have workout history."
                else:
                    status_msg = f"Loaded {insights_count} insights and {workout_count} workout histories. Warning: Cannot link data - missing email columns."
                    
            else:
                if workout_file:
                    messagebox.showwarning("Workout File Not Found", f"Workout history file not found: {workout_file}")
                status_msg = f"Loaded {insights_count} insights. No workout history loaded."
            
            self.status_var.set(status_msg)
            self.display_data_preview()
            self.start_review_btn.config(state='normal')
            return True
            
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to load CSV file(s):\n{str(e)}")
                self.status_var.set("Error loading data")
                self.start_review_btn.config(state='disabled')
            return False
            
    def display_data_preview(self):
        if self.insights_df is None:
            return
            
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        preview_columns = ['insight_text', 'email', 'goal', 'factuality_score', 'factuality_reasoning']
        available_columns = [col for col in preview_columns if col in self.insights_df.columns]
        
        self.tree['columns'] = available_columns
        
        for col in available_columns:
            self.tree.heading(col, text=col)
            if col == 'insight_text':
                self.tree.column(col, width=300, minwidth=200)
            elif col == 'factuality_reasoning':
                self.tree.column(col, width=300, minwidth=200)
            else:
                self.tree.column(col, width=150, minwidth=100)
        
        display_rows = min(50, len(self.insights_df))
        for index, row in self.insights_df.head(display_rows).iterrows():
            values = []
            for col in available_columns:
                value = str(row[col]) if pd.notna(row[col]) else ""
                if len(value) > 100:
                    value = value[:97] + "..."
                values.append(value)
            self.tree.insert('', 'end', values=values)
            
        if len(self.insights_df) > display_rows:
            self.tree.insert('', 'end', values=[f"... and {len(self.insights_df) - display_rows} more rows"] + [""] * (len(available_columns) - 1))
    
    def get_workout_history(self, email):
        if self.workout_history_df is None or 'email' not in self.workout_history_df.columns:
            return "No workout history data loaded."
            
        if 'workout_summary' not in self.workout_history_df.columns:
            return "Workout history data missing 'workout_summary' column."
            
        user_workouts = self.workout_history_df[self.workout_history_df['email'] == email]
        
        if user_workouts.empty:
            return f"No workout history found for: {email}"
            
        workout_summary = user_workouts.iloc[0]['workout_summary']
        return str(workout_summary) if pd.notna(workout_summary) else "Workout summary is empty."
    
    def generate_save_filename(self, insights_file, workout_file):
        insights_name = Path(insights_file).stem if insights_file else "unknown"
        workout_name = Path(workout_file).stem if workout_file else "unknown"
        
        combined = f"{insights_name}_{workout_name}"
        hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]
        
        filename = f"review_{insights_name}_{workout_name}_{hash_suffix}.json"
        return self.save_directory / filename
    
    def save_review_progress(self, reviews, current_insight_index, current_judge_index):
        if not self.current_save_file:
            return
            
        save_data = {
            "insights_file": self.insights_file_var.get(),
            "workout_file": self.workout_file_var.get(),
            "reviews": {str(k): v for k, v in reviews.items()},
            "current_insight_index": current_insight_index,
            "current_judge_index": current_judge_index,
            "last_saved": datetime.now().isoformat(),
            "total_insights": len(self.insights_df) if self.insights_df is not None else 0,
            "total_judges": len(self.judge_categories)
        }
        
        try:
            with open(self.current_save_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save progress: {e}")

    def _prompt_for_file(self, file_description, original_path):
        response = messagebox.askokcancel(
            "File Not Found",
            f"The {file_description} file could not be found at its original location:\n\n"
            f"{original_path}\n\n"
            "Would you like to locate it now?"
        )
        if response:
            new_path = filedialog.askopenfilename(
                title=f"Please locate your {file_description} file",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            return new_path if new_path else None
        return None

    def load_review_progress(self, save_file):
        try:
            with open(save_file, 'r') as f:
                save_data = json.load(f)

            insights_path = save_data.get("insights_file", "")
            workout_path = save_data.get("workout_file", "")
            paths_updated = False

            if not os.path.exists(insights_path):
                new_insights_path = self._prompt_for_file("Insights CSV", insights_path)
                if new_insights_path:
                    insights_path = new_insights_path
                    save_data["insights_file"] = new_insights_path
                    paths_updated = True
                else:
                    self.status_var.set("Load cancelled: Insights file not found.")
                    return None

            if workout_path and not os.path.exists(workout_path):
                new_workout_path = self._prompt_for_file("Workout History CSV", workout_path)
                if new_workout_path:
                    workout_path = new_workout_path
                    save_data["workout_file"] = new_workout_path
                    paths_updated = True
                else:
                    self.status_var.set("Load cancelled: Workout history file not found.")
                    return None

            self.insights_file_var.set(insights_path)
            self.workout_file_var.set(workout_path)

            if self.load_data(silent=True):
                self.current_save_file = save_file
                
                if paths_updated:
                    try:
                        with open(save_file, 'w') as f:
                            json.dump(save_data, f, indent=2)
                        self.status_var.set("File paths updated and review loaded.")
                    except Exception as e:
                        print(f"Failed to update save file paths: {e}")

                return save_data
            
            return None

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load review progress:\n{str(e)}")
            return None

    def find_existing_save_file(self, insights_file, workout_file):
        save_file = self.generate_save_filename(insights_file, workout_file)
        return save_file if save_file.exists() else None
    
    def get_last_review_file(self):
        save_files = list(self.save_directory.glob("review_*.json"))
        if not save_files:
            return None
        
        save_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return save_files[0]
    
    def update_load_button_state(self):
        last_file = self.get_last_review_file()
        if last_file:
            self.load_review_btn.configure(state='normal')
        else:
            self.load_review_btn.configure(state='disabled')
        
        save_files = list(self.save_directory.glob("review_*.json"))
        if save_files:
            self.load_file_btn.configure(state='normal')
        else:
            self.load_file_btn.configure(state='disabled')
    
    def start_new_review(self):
        insights_file = self.insights_file_var.get()
        workout_file = self.workout_file_var.get()
        
        existing_save = self.find_existing_save_file(insights_file, workout_file)
        
        if existing_save:
            response = messagebox.askyesnocancel(
                "Existing Review Found",
                f"A review is already in progress for these files.\n\n"
                f"Last saved: {datetime.fromtimestamp(existing_save.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"What would you like to do?\n\n"
                f"YES: Continue existing review\n"
                f"NO: Start fresh (previous progress will be lost)\n"
                f"CANCEL: Go back",
                default='yes'
            )
            
            if response is None:
                return
            elif response:
                self.load_existing_review(existing_save)
                return
            else:
                existing_save.unlink()
        
        self.current_save_file = self.generate_save_filename(insights_file, workout_file)
        self.start_review()
    
    def load_last_review(self):
        last_file = self.get_last_review_file()
        if not last_file:
            messagebox.showinfo("No Reviews", "No previous reviews found.")
            return
        
        self.load_existing_review(last_file)
    
    def load_specific_file(self):
        filename = filedialog.askopenfilename(
            title="Select Metajudge Save File",
            initialdir=self.save_directory,
            filetypes=[
                ("Metajudge Save Files", "*.json"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if not filename:
            return
        
        save_file = Path(filename)
        if not save_file.exists():
            messagebox.showerror("File Not Found", f"Save file not found: {filename}")
            return
        
        try:
            with open(save_file, 'r') as f:
                save_data = json.load(f)
            
            required_keys = ['insights_file', 'reviews', 'total_insights', 'total_judges']
            missing_keys = [key for key in required_keys if key not in save_data]
            
            if missing_keys:
                messagebox.showerror(
                    "Invalid Save File",
                    f"This doesn't appear to be a valid Metajudge save file.\n\n"
                    f"Missing required data: {', '.join(missing_keys)}"
                )
                return
                
        except (json.JSONDecodeError, Exception) as e:
            messagebox.showerror(
                "Invalid File Format",
                f"Could not read save file. Please ensure it's a valid JSON file.\n\n"
                f"Error: {str(e)}"
            )
            return
        
        self.load_existing_review(save_file)
    
    def load_existing_review(self, save_file):
        save_data = self.load_review_progress(save_file)
        if save_data:
            self.root.withdraw()
            
            saved_insight_index = save_data.get("current_insight_index", 0)
            total_insights = len(self.insights_df)

            if saved_insight_index >= total_insights:
                messagebox.showwarning(
                    "Progress Reset",
                    "The saved progress is beyond the number of insights in the loaded file.\n\n"
                    f"(Save file wanted insight #{saved_insight_index + 1}, but data file only has {total_insights} insights).\n\n"
                    "Your review will be reset to the beginning."
                )
                saved_insight_index = 0
                save_data['current_insight_index'] = 0
                save_data['current_judge_index'] = 0

            review_window = tk.Toplevel(self.root)
            review_app = ReviewWindow(review_window, self, self.FONTS)
            
            review_app.reviews = save_data.get("reviews", {})
            review_app.current_insight_index = saved_insight_index
            review_app.current_judge_index = save_data.get("current_judge_index", 0)
            
            if review_app.reviews and isinstance(list(review_app.reviews.keys())[0], str):
                review_app.reviews = {eval(k): v for k, v in review_app.reviews.items()}
            
            review_app.load_current_review()
            
            def on_review_close():
                review_app.on_window_close()
                self.root.deiconify()
            
            review_window.protocol("WM_DELETE_WINDOW", on_review_close)
            
            messagebox.showinfo("Review Loaded",
                                f"Loaded: {save_file.name}\n\n"
                                f"✓ {len(review_app.reviews)} completed assessments\n"
                                f"✓ Last saved: {save_data.get('last_saved', 'Unknown')}\n"
                                f"✓ Dataset: {len(save_data.get('reviews', {}))} reviews out of {save_data.get('total_insights', 0) * save_data.get('total_judges', 0)} total")
    
    def start_review(self):
        if self.insights_df is None:
            messagebox.showerror("Error", "No insights data loaded.")
            return
            
        self.root.withdraw()
            
        review_window = tk.Toplevel(self.root)
        review_app = ReviewWindow(review_window, self, self.FONTS)
        
        def on_review_close():
            review_app.on_window_close()
            self.root.deiconify()
        
        review_window.protocol("WM_DELETE_WINDOW", on_review_close)


class ReviewWindow:
    def __init__(self, window, main_app, fonts, testing_mode=False):
        self.window = window
        self.main_app = main_app
        self.FONTS = fonts
        self.current_insight_index = 0
        self.current_judge_index = 0
        
        self.reviews = {}
        self.testing_mode = testing_mode
        
        self.setup_review_ui()
        self.load_current_review()
        
    def setup_review_ui(self):
        self.window.title("Metajudge - Review Interface")
        self.window.geometry("1400x650")
        
        style = ttk.Style()
        style.configure("Assessment.TRadiobutton", font=(self.FONTS['default'][0], 11))
        
        main_container = ttk.Frame(self.window, padding="12")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.columnconfigure(2, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        top_nav_frame = ttk.Frame(main_container)
        top_nav_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        top_nav_frame.columnconfigure(1, weight=1)
        
        branding_frame = ttk.Frame(top_nav_frame)
        branding_frame.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(branding_frame, text="⚖️", font=(self.FONTS['large'][0], 20)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(branding_frame, text="Metajudge", font=(self.FONTS['medium'][0], 14, 'bold'),
                  foreground='#2c3e50').pack(side=tk.LEFT)
        
        progress_frame = ttk.Frame(top_nav_frame)
        progress_frame.grid(row=0, column=1)
        
        insight_nav_frame = ttk.Frame(progress_frame)
        insight_nav_frame.pack(pady=(0, 5))
        
        ttk.Label(insight_nav_frame, text="Insight", font=self.FONTS['default']).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(insight_nav_frame, text="◀", width=2, command=self.previous_insight).pack(side=tk.LEFT, padx=1)
        
        self.insight_entry_var = tk.StringVar()
        self.insight_entry = ttk.Entry(insight_nav_frame, textvariable=self.insight_entry_var, width=4, justify='center')
        self.insight_entry.pack(side=tk.LEFT, padx=2)
        self.insight_entry.bind('<Return>', self.jump_to_insight)
        self.insight_entry.bind('<FocusOut>', self.update_insight_display)
        
        ttk.Button(insight_nav_frame, text="▶", width=2, command=self.next_insight).pack(side=tk.LEFT, padx=1)
        
        self.insight_total_label = ttk.Label(insight_nav_frame, text="", font=self.FONTS['default'])
        self.insight_total_label.pack(side=tk.LEFT, padx=(5, 0))
        
        judge_nav_frame = ttk.Frame(progress_frame)
        judge_nav_frame.pack()
        
        ttk.Label(judge_nav_frame, text="Judge", font=self.FONTS['default']).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(judge_nav_frame, text="◀", width=2, command=self.previous_judge).pack(side=tk.LEFT, padx=1)
        
        self.judge_entry_var = tk.StringVar()
        self.judge_entry = ttk.Entry(judge_nav_frame, textvariable=self.judge_entry_var, width=4, justify='center')
        self.judge_entry.pack(side=tk.LEFT, padx=2)
        self.judge_entry.bind('<Return>', self.jump_to_judge)
        self.judge_entry.bind('<FocusOut>', self.update_judge_display)
        
        ttk.Button(judge_nav_frame, text="▶", width=2, command=self.next_judge).pack(side=tk.LEFT, padx=1)
        
        self.judge_total_label = ttk.Label(judge_nav_frame, text="of 7", font=self.FONTS['default'])
        self.judge_total_label.pack(side=tk.LEFT, padx=(5, 0))
        
        save_frame = ttk.Frame(top_nav_frame)
        save_frame.grid(row=1, column=1, pady=(8, 0))
        
        self.last_saved_var = tk.StringVar(value="Not saved yet")
        save_status_label = ttk.Label(save_frame, textvariable=self.last_saved_var,
                                      font=self.FONTS['small'], foreground='#7f8c8d')
        save_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        manual_save_btn = ttk.Button(save_frame, text="💾 Save Now", command=self.manual_save,
                                     style="Small.TButton")
        manual_save_btn.pack(side=tk.LEFT)
        
        save_style = ttk.Style()
        save_style.configure("Small.TButton", font=self.FONTS['small'])
        
        button_frame = ttk.Frame(top_nav_frame)
        button_frame.grid(row=0, column=2, sticky=tk.E)
        ttk.Button(button_frame, text="📊 View Statistics", command=self.show_statistics).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="💾 Export Results", command=self.export_results).pack(side=tk.LEFT)
        
        left_panel = ttk.LabelFrame(main_container, text="Insight Information", padding="12")
        left_panel.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 6))
        left_panel.columnconfigure(0, weight=1)
        
        ttk.Label(left_panel, text="Insight Text:", font=(self.FONTS['bold'][0], 11, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        self.insight_text = tk.Text(left_panel, height=5, wrap=tk.WORD, state='disabled',
                                    font=self.FONTS['default'], relief='solid', borderwidth=1)
        insight_scrollbar = ttk.Scrollbar(left_panel, orient='vertical', command=self.insight_text.yview)
        self.insight_text.configure(yscrollcommand=insight_scrollbar.set)
        self.insight_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        insight_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        user_info_frame = ttk.Frame(left_panel)
        user_info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        user_info_frame.columnconfigure(1, weight=1)
        
        ttk.Label(user_info_frame, text="User:", font=self.FONTS['bold']).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.email_var = tk.StringVar()
        ttk.Label(user_info_frame, textvariable=self.email_var, foreground='#0066cc',
                  font=self.FONTS['default']).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(user_info_frame, text="Goal:", font=self.FONTS['bold']).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(8, 0))
        self.goal_var = tk.StringVar()
        goal_label = ttk.Label(user_info_frame, textvariable=self.goal_var, wraplength=280,
                               font=self.FONTS['default'], foreground='#333333')
        goal_label.grid(row=1, column=1, sticky=(tk.W, tk.N), pady=(8, 0))
        
        center_panel = ttk.LabelFrame(main_container, text="Judge Score & Reasoning", padding="12")
        center_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=6)
        center_panel.columnconfigure(0, weight=1)
        
        judge_header_frame = ttk.Frame(center_panel)
        judge_header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 12))
        judge_header_frame.columnconfigure(0, weight=1)
        
        self.judge_info_var = tk.StringVar()
        self.judge_info_label = ttk.Label(judge_header_frame, textvariable=self.judge_info_var,
                                          font=(self.FONTS['medium'][0], 13, 'bold'), foreground='#2c3e50')
        self.judge_info_label.grid(row=0, column=0, sticky=tk.W)
        
        self.review_status_var = tk.StringVar()
        self.review_status_label = ttk.Label(judge_header_frame, textvariable=self.review_status_var,
                                             font=self.FONTS['bold'])
        self.review_status_label.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(center_panel, text="Judge Reasoning:", font=(self.FONTS['bold'][0], 11, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(0, 8))
        self.judge_reasoning_text = tk.Text(center_panel, height=6, wrap=tk.WORD, state='disabled',
                                            font=self.FONTS['default'], relief='solid', borderwidth=1)
        reasoning_scrollbar = ttk.Scrollbar(center_panel, orient='vertical', command=self.judge_reasoning_text.yview)
        self.judge_reasoning_text.configure(yscrollcommand=reasoning_scrollbar.set)
        self.judge_reasoning_text.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        reasoning_scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        
        self.assessment_frame = ttk.LabelFrame(center_panel, text="Your Assessment", padding="12")
        self.assessment_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.assessment_frame.columnconfigure(1, weight=1)
        
        radio_frame = ttk.Frame(self.assessment_frame)
        radio_frame.grid(row=0, column=0, columnspan=3, pady=(0, 12))
        
        self.issue_level_var = tk.StringVar(value="")
        
        self.no_issues_radio = ttk.Radiobutton(radio_frame, text="No Issues",
                                               variable=self.issue_level_var, value="No Issues",
                                               style="Assessment.TRadiobutton")
        self.no_issues_radio.grid(row=0, column=0, padx=(0, 30), sticky=tk.W)
        
        self.minor_issues_radio = ttk.Radiobutton(radio_frame, text="Minor Issues",
                                                  variable=self.issue_level_var, value="Minor Issues",
                                                  style="Assessment.TRadiobutton")
        self.minor_issues_radio.grid(row=0, column=1, padx=15, sticky=tk.W)
        
        self.major_issues_radio = ttk.Radiobutton(radio_frame, text="Major Issues",
                                                  variable=self.issue_level_var, value="Major Issues",
                                                  style="Assessment.TRadiobutton")
        self.major_issues_radio.grid(row=0, column=2, padx=(30, 0), sticky=tk.W)
        
        self.issue_level_var.trace_add('write', self.on_assessment_change)
        
        self._autosave_job = None
        
        ttk.Label(self.assessment_frame, text="Explanation (required for Minor/Major issues):",
                  font=self.FONTS['bold']).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
        self.explanation_text = tk.Text(self.assessment_frame, height=4, wrap=tk.WORD,
                                        font=self.FONTS['default'], relief='solid', borderwidth=1)
        explanation_scrollbar = ttk.Scrollbar(self.assessment_frame, orient='vertical', command=self.explanation_text.yview)
        self.explanation_text.configure(yscrollcommand=explanation_scrollbar.set)
        self.explanation_text.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
        explanation_scrollbar.grid(row=2, column=3, sticky=(tk.N, tk.S))
        
        self.explanation_text.bind('<KeyRelease>', self.on_assessment_change)
        
        self.autosave_var = tk.StringVar(value="")
        autosave_label = ttk.Label(self.assessment_frame, textvariable=self.autosave_var,
                                   font=('Segoe UI', 9), foreground='#7f8c8d')
        autosave_label.grid(row=3, column=1, pady=(10, 0))
        
        right_panel = ttk.LabelFrame(main_container, text="Workout History", padding="12")
        right_panel.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(6, 0))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        self.search_nav_frame = ttk.Frame(right_panel)
        self.search_nav_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.search_nav_frame.columnconfigure(1, weight=1)
        
        nav_btn_style = ttk.Style()
        nav_btn_style.configure("Nav.TButton", font=self.FONTS['small'])
        
        ttk.Button(self.search_nav_frame, text="◀ A", command=self.prev_search_match,
                   style="Nav.TButton").grid(row=0, column=0, padx=(0, 5))
        
        self.match_counter_var = tk.StringVar()
        self.match_counter_label = ttk.Label(self.search_nav_frame, textvariable=self.match_counter_var,
                                             font=self.FONTS['small'], foreground='#666666')
        self.match_counter_label.grid(row=0, column=1)
        
        ttk.Button(self.search_nav_frame, text="D ▶", command=self.next_search_match,
                   style="Nav.TButton").grid(row=0, column=2, padx=(5, 0))
        
        self.search_nav_frame.grid_remove()
        
        self.workout_history_text = tk.Text(right_panel, height=26, wrap=tk.WORD, state='disabled',
                                            font=self.FONTS['default'], relief='solid', borderwidth=1)
        workout_scrollbar = ttk.Scrollbar(right_panel, orient='vertical', command=self.workout_history_text.yview)
        self.workout_history_text.configure(yscrollcommand=workout_scrollbar.set)
        self.workout_history_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        workout_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        bottom_nav_frame = ttk.Frame(main_container)
        bottom_nav_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        bottom_nav_frame.columnconfigure(1, weight=1)
        
        nav_style = ttk.Style()
        nav_style.configure("Large.TButton", font=self.FONTS['medium'], padding=(20, 10))
        
        ttk.Button(bottom_nav_frame, text="← Previous", command=self.previous_review,
                   style="Large.TButton").grid(row=0, column=0, padx=(0, 10))
        ttk.Button(bottom_nav_frame, text="Next →", command=self.next_review,
                   style="Large.TButton").grid(row=0, column=2, padx=(10, 0))
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        self.current_search_matches = []
        self.current_match_index = -1
        self.search_term = ""
        
        self.judge_reasoning_text.bind('<<Selection>>', self.on_text_selection)
        self.judge_reasoning_text.bind('<Button-1>', self.on_text_click)
        self.insight_text.bind('<<Selection>>', self.on_text_selection)
        self.insight_text.bind('<Button-1>', self.on_text_click)
        
        self.setup_global_hotkeys()
    
    def manual_save(self):
        success = self.save_assessment_silent()
        if success:
            messagebox.showinfo("Saved", "Progress saved successfully!")
        else:
            self.main_app.save_review_progress(self.reviews, self.current_insight_index, self.current_judge_index)
            self.update_save_status()
            messagebox.showinfo("Saved", "Progress saved successfully!")
    
    def update_save_status(self):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_saved_var.set(f"Autosaved at: {timestamp}")
    
    def on_window_close(self):
        if self._autosave_job:
            self.window.after_cancel(self._autosave_job)
            self._autosave_job = None
        
        try:
            self.save_assessment_silent()
        except:
            pass
        
        self.window.destroy()
        
    def load_current_review(self):
        if self.main_app.insights_df is None or self.main_app.insights_df.empty:
            return
            
        insight_row = self.main_app.insights_df.iloc[self.current_insight_index]
        judge_category = self.main_app.judge_categories[self.current_judge_index]
        
        total_insights = len(self.main_app.insights_df)
        total_judges = len(self.main_app.judge_categories)
        
        self.insight_entry_var.set(str(self.current_insight_index + 1))
        self.insight_total_label.config(text=f"of {total_insights}")
        
        self.judge_entry_var.set(str(self.current_judge_index + 1))
        self.judge_total_label.config(text=f"of {total_judges}")
        
        self.email_var.set(str(insight_row.get('email', 'N/A')))
        self.goal_var.set(str(insight_row.get('goal', 'N/A')))
        
        self.insight_text.config(state='normal')
        self.insight_text.delete(1.0, tk.END)
        self.insight_text.insert(1.0, str(insight_row.get('insight_text', 'N/A')))
        self.insight_text.config(state='disabled')
        
        score_col = f'{judge_category}_score'
        reasoning_col = f'{judge_category}_reasoning'
        
        score = insight_row.get(score_col, 'N/A')
        reasoning = insight_row.get(reasoning_col, 'N/A')
        
        self.judge_info_var.set(f"{judge_category.title()} Judge - Score: {score}")
        
        self.judge_reasoning_text.config(state='normal')
        self.judge_reasoning_text.delete(1.0, tk.END)
        self.judge_reasoning_text.insert(1.0, str(reasoning))
        self.judge_reasoning_text.config(state='disabled')
        
        self.workout_history_text.config(state='normal')
        self.workout_history_text.delete(1.0, tk.END)
        email = insight_row.get('email', '')
        workout_history = self.main_app.get_workout_history(email)
        self.workout_history_text.insert(1.0, workout_history)
        self.workout_history_text.config(state='disabled')
        
        review_key = (self.current_insight_index, self.current_judge_index)
        if review_key in self.reviews:
            review = self.reviews[review_key]
            self.issue_level_var.set(review['issue_level'])
            self.explanation_text.delete(1.0, tk.END)
            self.explanation_text.insert(1.0, review['explanation'])
            self.review_status_var.set("✓ REVIEWED")
            self.review_status_label.configure(foreground='#27ae60')
        else:
            self.issue_level_var.set("")
            self.explanation_text.delete(1.0, tk.END)
            self.review_status_var.set("⏳ PENDING")
            self.review_status_label.configure(foreground='#e67e22')
        
        self.update_assessment_colors()
        self.clear_search_highlights()
    
    def save_assessment_silent(self):
        try:
            if not self.window or not self.window.winfo_exists():
                return False
        except tk.TclError:
            return False
            
        issue_level = self.issue_level_var.get()
        explanation = self.explanation_text.get(1.0, tk.END).strip()
        
        if not issue_level and not explanation:
            return False
        
        if issue_level in ['Minor Issues', 'Major Issues'] and not explanation:
            self.autosave_var.set("⚠ Explanation required for issues")
            return False
            
        review_key = (self.current_insight_index, self.current_judge_index)
        self.reviews[review_key] = {
            'issue_level': issue_level,
            'explanation': explanation
        }
        
        self.review_status_var.set("✓ REVIEWED")
        self.review_status_label.configure(foreground='#27ae60')
        self.autosave_var.set("✓ Auto-saved")
        
        self.main_app.save_review_progress(self.reviews, self.current_insight_index, self.current_judge_index)
        
        self.update_save_status()
        self.window.after(2000, lambda: self.autosave_var.set(""))
        
        return True
        
    def update_assessment_colors(self):
        issue_level = self.issue_level_var.get()
        style = ttk.Style()
        
        if issue_level == "No Issues":
            style.configure("GreenAssessment.TLabelframe", background="#e8f5e8")
            style.configure("GreenAssessment.TLabelframe.Label", background="#e8f5e8", foreground="#2e7d2e")
            self.assessment_frame.configure(style="GreenAssessment.TLabelframe")
        elif issue_level == "Minor Issues":
            style.configure("YellowAssessment.TLabelframe", background="#fff9e6")
            style.configure("YellowAssessment.TLabelframe.Label", background="#fff9e6", foreground="#cc9900")
            self.assessment_frame.configure(style="YellowAssessment.TLabelframe")
        elif issue_level == "Major Issues":
            style.configure("RedAssessment.TLabelframe", background="#ffeaea")
            style.configure("RedAssessment.TLabelframe.Label", background="#ffeaea", foreground="#cc0000")
            self.assessment_frame.configure(style="RedAssessment.TLabelframe")
        else:
            self.assessment_frame.configure(style="TLabelframe")
    
    def on_assessment_change(self, *args):
        try:
            if not self.window or not self.window.winfo_exists():
                return
        except tk.TclError:
            return
            
        self.update_assessment_colors()
        
        if not self.testing_mode:
            if self._autosave_job:
                self.window.after_cancel(self._autosave_job)
            self._autosave_job = self.window.after(500, self.safe_auto_save)
    
    def safe_auto_save(self):
        try:
            self.save_assessment_silent()
        except Exception:
            pass
        finally:
            self._autosave_job = None
    
    def next_review(self):
        self.save_assessment_silent()
        total_judges = len(self.main_app.judge_categories)
        total_insights = len(self.main_app.insights_df)
        
        if self.current_judge_index < total_judges - 1:
            self.current_judge_index += 1
        else:
            self.current_judge_index = 0
            if self.current_insight_index < total_insights - 1:
                self.current_insight_index += 1
            else:
                self.current_insight_index = 0
                
        self.load_current_review()
        
    def previous_review(self):
        self.save_assessment_silent()
        total_judges = len(self.main_app.judge_categories)
        
        if self.current_judge_index > 0:
            self.current_judge_index -= 1
        else:
            self.current_judge_index = total_judges - 1
            if self.current_insight_index > 0:
                self.current_insight_index -= 1
            else:
                self.current_insight_index = len(self.main_app.insights_df) - 1
                
        self.load_current_review()
    
    def previous_insight(self):
        self.save_assessment_silent()
        
        if self.current_insight_index > 0:
            self.current_insight_index -= 1
        else:
            self.current_insight_index = len(self.main_app.insights_df) - 1
        
        self.current_judge_index = 0
        self.load_current_review()
    
    def next_insight(self):
        self.save_assessment_silent()
        
        total_insights = len(self.main_app.insights_df)
        if self.current_insight_index < total_insights - 1:
            self.current_insight_index += 1
        else:
            self.current_insight_index = 0
        
        self.current_judge_index = 0
        self.load_current_review()
    
    def previous_judge(self):
        self.save_assessment_silent()
        
        total_judges = len(self.main_app.judge_categories)
        if self.current_judge_index > 0:
            self.current_judge_index -= 1
        else:
            self.current_judge_index = total_judges - 1
        
        self.load_current_review()
    
    def next_judge(self):
        self.save_assessment_silent()
        
        total_judges = len(self.main_app.judge_categories)
        if self.current_judge_index < total_judges - 1:
            self.current_judge_index += 1
        else:
            self.current_judge_index = 0
        
        self.load_current_review()
    
    def jump_to_insight(self, event=None):
        try:
            insight_num = int(self.insight_entry_var.get())
            total_insights = len(self.main_app.insights_df)
            
            if 1 <= insight_num <= total_insights:
                self.save_assessment_silent()
                self.current_insight_index = insight_num - 1
                self.current_judge_index = 0
                self.load_current_review()
            else:
                messagebox.showerror("Invalid Insight", f"Please enter a number between 1 and {total_insights}")
                self.update_insight_display()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
            self.update_insight_display()
    
    def jump_to_judge(self, event=None):
        try:
            judge_num = int(self.judge_entry_var.get())
            total_judges = len(self.main_app.judge_categories)
            
            if 1 <= judge_num <= total_judges:
                self.save_assessment_silent()
                self.current_judge_index = judge_num - 1
                self.load_current_review()
            else:
                messagebox.showerror("Invalid Judge", f"Please enter a number between 1 and {total_judges}")
                self.update_judge_display()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
            self.update_judge_display()
    
    def update_insight_display(self, event=None):
        self.insight_entry_var.set(str(self.current_insight_index + 1))
    
    def update_judge_display(self, event=None):
        self.judge_entry_var.set(str(self.current_judge_index + 1))
    
    def focus_insight_entry(self, event=None):
        self.insight_entry.focus_set()
        self.insight_entry.select_range(0, tk.END)
        return 'break'
    
    def focus_judge_entry(self, event=None):
        self.judge_entry.focus_set()
        self.judge_entry.select_range(0, tk.END)
        return 'break'
    
    def hotkey_no_issues(self, event=None):
        if self.is_actively_typing(event):
            return
        
        self.issue_level_var.set("No Issues")
        self.save_assessment_silent()
        self.window.after(100, self.next_review)
        return 'break'
    
    def hotkey_minor_issues(self, event=None):
        if self.is_actively_typing(event):
            return
        
        self.issue_level_var.set("Minor Issues")
        self.explanation_text.focus_set()
        return 'break'
    
    def hotkey_major_issues(self, event=None):
        if self.is_actively_typing(event):
            return
        
        self.issue_level_var.set("Major Issues")
        self.explanation_text.focus_set()
        return 'break'
    
    def is_actively_typing(self, event=None):
        if not event:
            return False
        
        if (isinstance(event.widget, tk.Text) and
            event.widget == self.explanation_text and
            str(event.widget.cget('state')) != 'disabled'):
            return True
        
        if isinstance(event.widget, ttk.Entry):
            return True
        
        return False
    
    def setup_global_hotkeys(self):
        widgets_to_bind = [
            self.window, self.insight_text, self.judge_reasoning_text,
            self.explanation_text, self.insight_entry, self.judge_entry
        ]
        
        for widget in widgets_to_bind:
            widget.bind('<Key-1>', self.hotkey_no_issues)
            widget.bind('<Key-2>', self.hotkey_minor_issues)
            widget.bind('<Key-3>', self.hotkey_major_issues)
            widget.bind('<Key-a>', self.prev_search_match)
            widget.bind('<Key-d>', self.next_search_match)
            widget.bind('<Control-Left>', lambda e: self.previous_insight())
            widget.bind('<Control-Right>', lambda e: self.next_insight())
            widget.bind('<Control-Up>', lambda e: self.previous_judge())
            widget.bind('<Control-Down>', lambda e: self.next_judge())
            widget.bind('<Control-i>', self.focus_insight_entry)
            widget.bind('<Control-j>', self.focus_judge_entry)
    
    def on_text_selection(self, event=None):
        try:
            selected = None
            try:
                selected = self.judge_reasoning_text.selection_get()
            except tk.TclError:
                try:
                    selected = self.insight_text.selection_get()
                except tk.TclError:
                    pass
            
            if selected and len(selected.strip()) > 1:
                self.search_in_workout_history(selected.strip())
            else:
                self.clear_search_highlights()
        except tk.TclError:
            self.clear_search_highlights()
    
    def on_text_click(self, event=None):
        self.window.after(50, self.check_selection)
    
    def check_selection(self):
        try:
            has_selection = False
            try:
                self.judge_reasoning_text.selection_get()
                has_selection = True
            except tk.TclError:
                try:
                    self.insight_text.selection_get()
                    has_selection = True
                except tk.TclError:
                    pass
            
            if not has_selection:
                self.clear_search_highlights()
        except tk.TclError:
            self.clear_search_highlights()
    
    def search_in_workout_history(self, search_term):
        self.search_term = search_term.lower()
        self.current_search_matches = []
        self.current_match_index = -1
        
        self.workout_history_text.tag_remove('search_match', '1.0', tk.END)
        self.workout_history_text.tag_remove('current_match', '1.0', tk.END)
        
        self.workout_history_text.tag_configure('search_match', background='#ffeb3b', foreground='black')
        self.workout_history_text.tag_configure('current_match', background='#1565c0', foreground='white')
        
        full_text = self.workout_history_text.get('1.0', tk.END).lower()
        
        start_idx = 0
        while True:
            pos = full_text.find(self.search_term, start_idx)
            if pos == -1:
                break
            
            line_start = full_text.count('\n', 0, pos) + 1
            char_start = pos - full_text.rfind('\n', 0, pos) - 1
            if char_start < 0:
                char_start = pos
            
            start_pos = f"{line_start}.{char_start}"
            end_pos = f"{line_start}.{char_start + len(self.search_term)}"
            
            self.current_search_matches.append((start_pos, end_pos))
            start_idx = pos + 1
        
        for start_pos, end_pos in self.current_search_matches:
            self.workout_history_text.tag_add('search_match', start_pos, end_pos)
        
        if self.current_search_matches:
            self.current_match_index = 0
            self.highlight_current_match()
            self.show_search_navigation()
            self.window.title(f"Metajudge - {len(self.current_search_matches)} matches for '{search_term}'")
        else:
            self.hide_search_navigation()
            self.window.title("Metajudge - Judge Evaluation Review Tool")
    
    def highlight_current_match(self):
        if 0 <= self.current_match_index < len(self.current_search_matches):
            self.workout_history_text.tag_remove('current_match', '1.0', tk.END)
            
            start_pos, end_pos = self.current_search_matches[self.current_match_index]
            self.workout_history_text.tag_add('current_match', start_pos, end_pos)
            self.workout_history_text.see(start_pos)
            
            total_matches = len(self.current_search_matches)
            current_num = self.current_match_index + 1
            self.window.title(f"Metajudge - Match {current_num}/{total_matches} for '{self.search_term}'")
            self.match_counter_var.set(f"{current_num}/{total_matches} matches for '{self.search_term}'")
    
    def next_search_match(self, event=None):
        if not self.current_search_matches or self.is_actively_typing(event):
            return
            
        self.current_match_index = (self.current_match_index + 1) % len(self.current_search_matches)
        self.highlight_current_match()
        return 'break'
    
    def prev_search_match(self, event=None):
        if not self.current_search_matches or self.is_actively_typing(event):
            return
            
        self.current_match_index = (self.current_match_index - 1) % len(self.current_search_matches)
        self.highlight_current_match()
        return 'break'
    
    def show_search_navigation(self):
        self.search_nav_frame.grid()
    
    def hide_search_navigation(self):
        self.search_nav_frame.grid_remove()
    
    def clear_search_highlights(self):
        self.workout_history_text.tag_remove('search_match', '1.0', tk.END)
        self.workout_history_text.tag_remove('current_match', '1.0', tk.END)
        self.current_search_matches = []
        self.current_match_index = -1
        self.search_term = ""
        self.hide_search_navigation()
        self.window.title("Metajudge - Judge Evaluation Review Tool")
    
    def show_statistics(self):
        stats_window = tk.Toplevel(self.window)
        StatisticsWindow(stats_window, self, self.FONTS)
    
    def _show_export_dialog(self):
        """Creates a modal dialog to ask the user for the export format."""
        dialog = tk.Toplevel(self.window)
        dialog.title("Export Options")
        
        x = self.window.winfo_x()
        y = self.window.winfo_y()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        dialog.geometry(f"300x120+{x + w//2 - 150}+{y + h//2 - 60}")
        
        dialog.transient(self.window)
        dialog.grab_set()

        choice = tk.StringVar()

        def set_choice_and_close(sort_order):
            choice.set(sort_order)
            dialog.destroy()

        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="Choose export sort order:").pack(pady=(0, 10))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()

        insight_btn = ttk.Button(button_frame, text="Sort by Insight", command=lambda: set_choice_and_close('insight'))
        insight_btn.pack(side="left", padx=5)

        judge_btn = ttk.Button(button_frame, text="Sort by Judge", command=lambda: set_choice_and_close('judge'))
        judge_btn.pack(side="left", padx=5)

        self.window.wait_window(dialog)
        
        return choice.get()

    def export_results(self):
        """Show a dialog to choose the export format and then export."""
        if not self.reviews:
            messagebox.showwarning("No Data", "No reviews completed yet. Complete some reviews before exporting.")
            return
            
        sort_choice = self._show_export_dialog()

        if sort_choice:
            self._perform_export(sort_by=sort_choice)

    def _perform_export(self, sort_by):
        """Generates and saves the CSV file with the chosen sort order."""
        default_filename = f"metajudge_results_{sort_by}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filename = filedialog.asksaveasfilename(
            title=f"Save Results (Sorted by {sort_by.title()})",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_filename
        )
        
        if not filename:
            return
            
        try:
            export_data = []
            for (insight_idx, judge_idx), review in self.reviews.items():
                insight_row = self.main_app.insights_df.iloc[insight_idx]
                judge_category = self.main_app.judge_categories[judge_idx]
                
                score_col = f'{judge_category}_score'
                reasoning_col = f'{judge_category}_reasoning'
                
                export_row = {
                    'insight_index': insight_idx + 1,
                    'judge_category': judge_category,
                    'metajudge_assessment': review['issue_level'],
                    'metajudge_explanation': review['explanation'],
                    'judge_score': insight_row.get(score_col, ''),
                    'judge_reasoning': insight_row.get(reasoning_col, ''),
                    'insight_text': insight_row.get('insight_text', ''),
                    'user_email': insight_row.get('email', ''),
                    'user_goal': insight_row.get('goal', ''),
                    'review_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                export_data.append(export_row)
            
            export_df = pd.DataFrame(export_data)

            if sort_by == 'judge':
                export_df.sort_values(by=['judge_category', 'insight_index'], inplace=True)
            else:
                export_df.sort_values(by=['insight_index', 'judge_category'], inplace=True)
            
            column_order = [
                'judge_category', 'insight_index', 'metajudge_assessment', 
                'metajudge_explanation', 'judge_score', 'judge_reasoning',
                'insight_text', 'user_email', 'user_goal', 'review_timestamp'
            ]
            export_df = export_df[column_order]

            export_df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export Complete", f"Successfully exported {len(export_data)} reviews to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")


class StatisticsWindow:
    def __init__(self, window, review_window, fonts):
        self.window = window
        self.review_window = review_window
        self.main_app = review_window.main_app
        self.FONTS = fonts
        
        self.setup_stats_ui()
        self.calculate_and_display_stats()
        
    def setup_stats_ui(self):
        self.window.title("Judge Performance Statistics")
        self.window.geometry("700x700")
        
        main_container = ttk.Frame(self.window, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_container, text="Judge Performance Statistics", font=self.FONTS['large'])
        title_label.pack(pady=(0, 10))
        
        ttk.Button(main_container, text="💾 Export Statistics", command=self.export_statistics).pack(pady=(0, 20))
        
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(canvas.find_all()[0], width=canvas_width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.setup_combined_view()
    
    def setup_combined_view(self):
        overall_frame = ttk.LabelFrame(self.scrollable_frame, text="📊 Overall Review Summary", padding="15")
        overall_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.summary_text = tk.Text(overall_frame, height=8, wrap=tk.WORD, state='disabled',
                                    font=self.FONTS['default'], relief='solid', borderwidth=1)
        summary_scrollbar = ttk.Scrollbar(overall_frame, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        judge_frame = ttk.LabelFrame(self.scrollable_frame, text="🎯 Performance by Judge Category", padding="15")
        judge_frame.pack(fill=tk.BOTH, expand=True)
        
        self.judge_details_text = tk.Text(judge_frame, wrap=tk.WORD, state='disabled',
                                          font=self.FONTS['mono'], relief='solid', borderwidth=1)
        judge_details_scrollbar = ttk.Scrollbar(judge_frame, orient='vertical', command=self.judge_details_text.yview)
        self.judge_details_text.configure(yscrollcommand=judge_details_scrollbar.set)
        
        self.judge_details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        judge_details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def calculate_and_display_stats(self):
        reviews = self.review_window.reviews
        total_insights = len(self.main_app.insights_df)
        total_judges = len(self.main_app.judge_categories)
        total_possible_reviews = total_insights * total_judges
        
        total_completed = len(reviews)
        no_issues = sum(1 for r in reviews.values() if r['issue_level'] == 'No Issues')
        minor_issues = sum(1 for r in reviews.values() if r['issue_level'] == 'Minor Issues')
        major_issues = sum(1 for r in reviews.values() if r['issue_level'] == 'Major Issues')
        
        no_issues_pct = (no_issues / total_completed * 100) if total_completed > 0 else 0
        minor_issues_pct = (minor_issues / total_completed * 100) if total_completed > 0 else 0
        major_issues_pct = (major_issues / total_completed * 100) if total_completed > 0 else 0
        completion_pct = (total_completed / total_possible_reviews * 100) if total_possible_reviews > 0 else 0
        
        summary_text = f"""METAJUDGE REVIEW SUMMARY
{'=' * 50}

Progress:
• Total Reviews Completed: {total_completed:,} of {total_possible_reviews:,} ({completion_pct:.1f}%)
• Insights Reviewed: {len(set(key[0] for key in reviews.keys()))} of {total_insights}
• Judge Categories: {total_judges}

Issue Distribution:
• No Issues: {no_issues:,} ({no_issues_pct:.1f}%)
• Minor Issues: {minor_issues:,} ({minor_issues_pct:.1f}%)
• Major Issues: {major_issues:,} ({major_issues_pct:.1f}%)

Overall Issue Rate: {((minor_issues + major_issues) / total_completed * 100) if total_completed > 0 else 0:.1f}%
"""
        
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary_text)
        self.summary_text.config(state='disabled')
        
        judge_stats = {}
        for (insight_idx, judge_idx), review in reviews.items():
            judge_name = self.main_app.judge_categories[judge_idx]
            if judge_name not in judge_stats:
                judge_stats[judge_name] = {'no_issues': 0, 'minor_issues': 0, 'major_issues': 0, 'total': 0}
            
            judge_stats[judge_name]['total'] += 1
            if review['issue_level'] == 'No Issues':
                judge_stats[judge_name]['no_issues'] += 1
            elif review['issue_level'] == 'Minor Issues':
                judge_stats[judge_name]['minor_issues'] += 1
            elif review['issue_level'] == 'Major Issues':
                judge_stats[judge_name]['major_issues'] += 1
        
        judge_details = "DETAILED JUDGE PERFORMANCE BREAKDOWN\n"
        judge_details += "=" * 70 + "\n\n"
        
        judge_list = []
        for judge_name in self.main_app.judge_categories:
            stats = judge_stats.get(judge_name, {'no_issues': 0, 'minor_issues': 0, 'major_issues': 0, 'total': 0})
            issue_rate = ((stats['minor_issues'] + stats['major_issues']) / stats['total'] * 100) if stats['total'] > 0 else 0
            judge_list.append((judge_name, stats, issue_rate))
        
        judge_list.sort(key=lambda x: x[2], reverse=True)
        
        for i, (judge_name, stats, issue_rate) in enumerate(judge_list):
            if i > 0:
                judge_details += "\n" + "-" * 50 + "\n\n"
            
            judge_details += f"{judge_name.upper()} JUDGE\n"
            judge_details += f"Total Reviews: {stats['total']}\n\n"
            
            if stats['total'] > 0:
                no_issues_pct = (stats['no_issues'] / stats['total'] * 100)
                minor_issues_pct = (stats['minor_issues'] / stats['total'] * 100)
                major_issues_pct = (stats['major_issues'] / stats['total'] * 100)
                
                judge_details += f"Issue Distribution:\n"
                judge_details += f"• No Issues:    {stats['no_issues']:3d} ({no_issues_pct:5.1f}%)\n"
                judge_details += f"• Minor Issues: {stats['minor_issues']:3d} ({minor_issues_pct:5.1f}%)\n"
                judge_details += f"• Major Issues: {stats['major_issues']:3d} ({major_issues_pct:5.1f}%)\n\n"
                judge_details += f"Overall Issue Rate: {issue_rate:.1f}%\n"
            else:
                judge_details += "No reviews completed yet.\n"
        
        self.judge_details_text.config(state='normal')
        self.judge_details_text.delete(1.0, tk.END)
        self.judge_details_text.insert(1.0, judge_details)
        self.judge_details_text.config(state='disabled')
    
    def export_statistics(self):
        reviews = self.review_window.reviews
        
        if not reviews:
            messagebox.showwarning("No Data", "No reviews completed yet. Complete some reviews before exporting statistics.")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Save Judge Statistics",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"judge_statistics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
            
        try:
            judge_stats = {}
            for (insight_idx, judge_idx), review in reviews.items():
                judge_name = self.main_app.judge_categories[judge_idx]
                if judge_name not in judge_stats:
                    judge_stats[judge_name] = {'no_issues': 0, 'minor_issues': 0, 'major_issues': 0, 'total': 0}
                
                judge_stats[judge_name]['total'] += 1
                if review['issue_level'] == 'No Issues':
                    judge_stats[judge_name]['no_issues'] += 1
                elif review['issue_level'] == 'Minor Issues':
                    judge_stats[judge_name]['minor_issues'] += 1
                elif review['issue_level'] == 'Major Issues':
                    judge_stats[judge_name]['major_issues'] += 1
            
            export_data = []
            for judge_name in self.main_app.judge_categories:
                stats = judge_stats.get(judge_name, {'no_issues': 0, 'minor_issues': 0, 'major_issues': 0, 'total': 0})
                issue_rate = ((stats['minor_issues'] + stats['major_issues']) / stats['total'] * 100) if stats['total'] > 0 else 0
                
                export_row = {
                    'judge_category': judge_name,
                    'total_reviews': stats['total'],
                    'no_issues_count': stats['no_issues'],
                    'minor_issues_count': stats['minor_issues'],
                    'major_issues_count': stats['major_issues'],
                    'issue_rate_percent': round(issue_rate, 1),
                    'no_issues_percent': round((stats['no_issues'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1),
                    'minor_issues_percent': round((stats['minor_issues'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1),
                    'major_issues_percent': round((stats['major_issues'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1),
                    'export_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                export_data.append(export_row)
            
            export_data.sort(key=lambda x: x['issue_rate_percent'], reverse=True)
            
            export_df = pd.DataFrame(export_data)
            export_df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export Complete", f"Successfully exported judge statistics to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export statistics:\n{str(e)}")


def main():
    root = tk.Tk()
    app = MetajudgeApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()