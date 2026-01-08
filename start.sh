#!/usr/bin/env bash

docker compose -f docker/docker-compose.yml down --remove-orphans && docker compose -f docker/docker-compose.yml up --remove-orphans --build
