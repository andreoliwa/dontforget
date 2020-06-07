# Don't Forget

Don't forget to complete your tasks, using Todoist, Toggle and Node-RED integrations.

To install the script:

    make install

To start the app on the status bar:

    dontforget

# Notes

- This app is based on [rumps](https://github.com/jaredks/rumps), it runs in the macOS status bar.
- It only runs on macOS for now.
- I considered using [Dramatiq](https://dramatiq.io/) for background tasks, but that would need a local RabbitMQ or a Redis instance.
  Although Docker could be used, it would be too heavy for a local app that is meant to run on the status bar all the time. There will be not enough load to justify a distributed task queue.
