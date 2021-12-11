FROM debian:buster-slim

RUN apt-get update 

WORKDIR /build-temp

# Copy build scripts into the container and run them

COPY soil/deps-apt.sh /build-temp/soil/deps-apt.sh
RUN soil/deps-apt.sh cpp

COPY soil/deps-tar.sh /build-temp/soil/deps-tar.sh
RUN soil/deps-tar.sh cpp

CMD ["sh", "-c", "echo 'hello from oilshell/soil-cpp buildkit'"]
