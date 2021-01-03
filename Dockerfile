FROM ubuntu:20.04
RUN apt-get update && apt-get install python3 python3-pip -y
COPY ./ /
RUN /install.sh
EXPOSE 8765
CMD ["/bin/bash"]