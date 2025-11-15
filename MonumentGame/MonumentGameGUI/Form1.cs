using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace MonumentGameGUI
{
    public partial class Form1 : Form
    {
        private Dictionary<string, List<string>> monuments;
        private string chosenMonument;
        private List<string> hints;
        private int attempts = 3;

        public Form1()
        {
            InitializeComponent();
            InitializeGame();
        }

        private void InitializeGame()
        {
            this.Text = "🌟 Guess the Monument Game 🌟";
            this.Size = new Size(500, 400);
            this.BackColor = Color.LightYellow;

            monuments = new Dictionary<string, List<string>>()
            {
                {"Turnul Eiffel", new List<string>{"Se află în Paris 🗼", "Construit din metal", "Simbol al Franței 🇫🇷"}},
                {"Colosseum", new List<string>{"Se află în Roma 🏛️", "Arena antică", "Capacitate ~50.000 spectatori"}},
                {"Machu Picchu", new List<string>{"Se află în Peru 🏞️", "Oraș antic Inca", "În munți ⛰️"}}
            };

            var rnd = new Random();
            var keys = new List<string>(monuments.Keys);
            chosenMonument = keys[rnd.Next(keys.Count)];
            hints = monuments[chosenMonument];

            SetupUI();
        }

        private TextBox inputBox;
        private Button guessButton;
        private Label hintLabel1;
        private Label hintLabel2;
        private Label messageLabel;

        private void SetupUI()
        {
            hintLabel1 = new Label() { Text = "🕵️‍♂️ Hint 1: " + hints[0], Location = new Point(20, 20), AutoSize = true };
            hintLabel2 = new Label() { Text = "🕵️‍♀️ Hint 2: " + hints[1], Location = new Point(20, 50), AutoSize = true };
            messageLabel = new Label() { Text = "You have 3 attempts! 💪", Location = new Point(20, 80), AutoSize = true, ForeColor = Color.DarkBlue };

            inputBox = new TextBox() { Location = new Point(20, 120), Width = 250 };
            guessButton = new Button() { Text = "Guess 🎯", Location = new Point(280, 118), Width = 80 };

            guessButton.Click += GuessButton_Click;

            this.Controls.Add(hintLabel1);
            this.Controls.Add(hintLabel2);
            this.Controls.Add(messageLabel);
            this.Controls.Add(inputBox);
            this.Controls.Add(guessButton);
        }

        private void GuessButton_Click(object sender, EventArgs e)
        {
            string guess = inputBox.Text.Trim();
            if (string.IsNullOrEmpty(guess)) return;

            if (guess.Equals(chosenMonument, StringComparison.OrdinalIgnoreCase))
            {
                messageLabel.Text = $"🎉 Correct! The monument was {chosenMonument} 🏆";
                messageLabel.ForeColor = Color.Green;
                guessButton.Enabled = false;
            }
            else
            {
                attempts--;
                if (attempts > 0)
                {
                    messageLabel.Text = $"❌ Incorrect! {attempts} attempts left. Try again!";
                    messageLabel.ForeColor = Color.Red;
                }
                else
                {
                    messageLabel.Text = $"💔 Out of attempts! The monument was {chosenMonument}.";
                    messageLabel.ForeColor = Color.DarkRed;
                    guessButton.Enabled = false;
                }
            }
        }
    }
}
