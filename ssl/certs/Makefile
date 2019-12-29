# Deliberately customized from: https://gist.github.com/xenogenesi/1b2137f769aa80b6c99d573071f5d086

DOMAIN ?= mydomain.com
NAME ?= $(DOMAIN)

COUNTRY := IT
STATE := IT
COMPANY := Evil Corp.

# credits to: https://gist.github.com/fntlnz/cf14feb5a46b2eda428e000157447309

# usage:
# make rootCA.crt # (rootCA.key implicitly created)
# make DOMAIN=somedomain.dev somedomain.dev.csr somedomain.dev.crt   or   make DOMAIN=somedomain.dev
# make DOMAIN=somedomain.dev verify-csr
# make DOMAIN=somedomain.dev verify-crt

# import rootCA.crt to the client (chrome)
# upload somedomain.dev.crt   and   somedomain.dev.key   to the host

all: $(NAME).csr $(NAME).crt


rootCA.key:
	openssl genrsa -out rootCA.key 4096

# create and self sign root certificate
rootCA.crt: rootCA.key
	echo -ne "$(COUNTRY)\n$(STATE)\n\n$(COMPANY)\n\n\n\n" | openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out $@

$(NAME).key:
	openssl genrsa -out $(NAME).key 2048

$(NAME).conf:
	sh mkconf.sh $(NAME) > $(NAME).conf

$(NAME).csr: $(NAME).key $(NAME).conf
	openssl req -new -sha256 -key $(NAME).key -subj "/C=$(COUNTRY)/ST=$(STATE)/O=$(COMPANY)/CN=$(DOMAIN)" \
		-reqexts SAN \
		-config $(NAME).conf \
		-out $(NAME).csr

# verify .csr content
.PHONY: verify-csr
verify-csr:
	openssl req  -in $(NAME).csr -noout -text

$(NAME).san.conf:
	sh mksan.sh $(DOMAIN) $(COUNTRY) $(STATE) "$(COMPANY)" >$@

$(NAME).crt: rootCA.key rootCA.crt $(NAME).csr $(NAME).san.conf
	openssl x509 -req -in $(NAME).csr -CA ./rootCA.crt -CAkey ./rootCA.key \
		-CAcreateserial -out $@ -days 500 -sha256 \
		-extfile $(NAME).san.conf -extensions req_ext

# verify the certificate
.PHONY: verify-crt
verify-crt:
	openssl x509 -in $(NAME).crt -text -noout

.PHONY: clean
clean:
	-rm -f $(NAME).key $(NAME).csr $(NAME).conf $(NAME).san.conf $(NAME).crt
