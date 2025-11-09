#FROM nexryai/camera.ui:alpine
#RUN apk add --no-cache ffmpeg
FROM nexryai/camera.ui:alpine
USER root
RUN sed -i 's|/v[0-9.]\+/|/edge/|g' /etc/apk/repositories || true \
 && apk update \
 && apk add --no-cache ffmpeg curl ca-certificates