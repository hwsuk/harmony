# Harmony Discord Bot

![GitHub release badge](https://img.shields.io/github/v/release/hwsuk/harmony?logo=github)

Harmony is a bot designed to make moderating companion Discord servers for subreddits easier, particularly for trading subreddits. Features include:

- Linking Discord and Reddit accounts with a companion subreddit, to gain privileged roles.
- Allowing moderators to assign roles based on a community member's standing, updating their subreddit flair in turn.
- Searching eBay to help members get an idea of how to price their items.

> This bot is currently designed to run in a single guild. As such, if you want to use it, you will need to host it yourself.

## Requirements

- Python >= 3.11
- MongoDB (with a replica set configured, authentication enabled, and a user authorised to read from and write to a dedicated database)
- Optional (recommended for local development): A test account with its own test subreddit (of which that account is a moderator) 
- Optional (recommended for production deployments): Docker

## Development Setup

Once you have the [required software installed to begin development](#requirements):

- Clone this repository.
- Copy the `config.example.json` file to `config.json` and fill in values according to the [config file documentation](#config-file-documentation).
- Run `main.py` and cross your fingers 🤞

## Production Deployment

You can use the included `docker-compose.yml` to carry out a production deployment with Docker. New releases are automatically built and pushed to Docker Hub.

## User Guide

You can read the User Guide [here](docs/user-guide.md). This details how to use the bot from a user's perspective.

## Configuration Guide

You can read the Configuration Guide [here](docs/configuration-guide.md). This details how to configure the bot, for local development or for a production deployment.