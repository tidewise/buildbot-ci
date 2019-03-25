FROM ruby:2.5.1

RUN mkdir -p /var/cache/gem
RUN gem install --no-ri --no-rdoc -v 2.0.0 gemstash
COPY config.yml /etc/gemstash.yml

CMD ["gemstash", "start", "--no-daemonize", "--config-file", "/etc/gemstash.yml"]
