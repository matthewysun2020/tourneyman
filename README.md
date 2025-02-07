# tourneyman

An app designed to allow for easier hosting of small tournaments - built for your ease of use.

## Why tourneyman?

There are many apps that allow for the creation of tournament brackets, but this seeks to be an all-in-one tool that is easy to use and visually pleasing. The goal of this application is to allow tournament hosts to easily set up a tournament, input results, and view the bracket.

The app is designed to be intuitive, as easy as possible to pick up and use for anyone, regardless of technical expertise or prowess.

## What's being worked on?

The bracket viewer still needs to be implemented. (Yes, I know this is probably the most important/valuable part of the application. I'm working on it!)

## Planned features

- Multiple tournament formats (single elimination, double elimination, round robin, Swiss, etc.)
- Quick and simple tournament registration (via any device connected to the network)
- Quick and simple match result submission (via any device connected to the network)
- Clean bracket viewing experience, specifically laid out for each tournament format
- Multiple tournaments at the same time (ID differentiation)
- Compatibility for any OS (currently only Windows and Linux supported)

## How does this work? (WIP)

The app uses the Flask and SQLAlchemy packages to host a server containing all your tournament information (players, match results). The app will take care of installing any missing dependencies on your local machine, and you'll only need to run the app to get started.

## How do I use the app? (WIP)

**1. Run the application.** The app will return a URL that you can access that takes you to the homepage for the tournament manager. NOTE: Currently, the proper way to launch this application is to navigate to its directory in a CLI and run `python main.py`.

**2. Create a new tournament.** Click the New Tournament button, enter an name, select a tournament format, and choose start and end dates.

**3. Add players to the tournament.** Click the Add Players button and add your players! Note that duplicate player names are not allowed. FUTURE FEATURE: Add players that you've added to other tournaments.

From here, you can click the Match Management button and register the results of a match or give a player a bye or update different aspects of the tournament. Once it detects that there's only one player left, it will automatically mark the tournament as complete.
The application, while it runs, is accessible from any device on the same network as the host. Just access the same URL from the browser. (The app is currently configured to run on 192.168.x.x:5000, where the x's are replaced with the host's local IP.)
