"use strict";

export class VideoConnection {
    constructor(
        videoElement,
        offerUrl,
        { onStateChange = null, reconnectDelayMs = 2000 } = {},
    ) {
        if (!(videoElement instanceof HTMLVideoElement)) {
            throw new TypeError("videoElement must be an HTMLVideoElement");
        }

        if (typeof offerUrl !== "string" || offerUrl.trim() === "") {
            throw new TypeError("offerUrl must be a non-empty string");
        }

        if (onStateChange !== null && typeof onStateChange !== "function") {
            throw new TypeError("onStateChange must be a function or null");
        }

        if (!Number.isFinite(reconnectDelayMs) || reconnectDelayMs < 0) {
            throw new TypeError(
                "reconnectDelayMs must be a non-negative number",
            );
        }

        this.videoElement = videoElement;
        this.offerUrl = offerUrl.trim();
        this.onStateChange = onStateChange;
        this.reconnectDelayMs = reconnectDelayMs;

        this.peerConnection = null;
        this.reconnectTimer = null;
        this.closed = false;
        this.connecting = false;
    }

    setState(state) {
        if (typeof this.onStateChange === "function") {
            this.onStateChange(state);
        }
    }

    async connect() {
        if (this.closed || this.connecting) {
            return;
        }

        this.connecting = true;
        this.clearReconnect();

        try {
            await this.closePeer();

            if (this.closed) {
                return;
            }

            this.setState("connecting");

            const peerConnection = new RTCPeerConnection();

            this.peerConnection = peerConnection;

            peerConnection.ontrack = (event) => {
                if (this.peerConnection !== peerConnection) {
                    return;
                }

                const stream = event.streams[0];

                if (stream === undefined) {
                    return;
                }

                this.videoElement.srcObject = stream;

                this.setState("connected");
            };

            peerConnection.onconnectionstatechange = () => {
                if (this.peerConnection !== peerConnection) {
                    return;
                }

                const state = peerConnection.connectionState;

                if (state === "connected") {
                    this.setState("connected");
                    return;
                }

                if (
                    state === "failed" ||
                    state === "disconnected" ||
                    state === "closed"
                ) {
                    this.setState("disconnected");
                    this.scheduleReconnect();
                }
            };

            peerConnection.addTransceiver("video", {
                direction: "recvonly",
            });

            const offer = await peerConnection.createOffer();

            await peerConnection.setLocalDescription(offer);

            const localDescription = peerConnection.localDescription;

            if (localDescription === null) {
                throw new Error("WebRTC local description is unavailable");
            }

            const response = await fetch(this.offerUrl, {
                method: "POST",
                cache: "no-store",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    sdp: localDescription.sdp,
                    type: localDescription.type,
                }),
            });

            if (!response.ok) {
                const details = await response.text();

                throw new Error(
                    `Vision offer failed: ` + `${response.status} ` + details,
                );
            }

            const answer = await response.json();

            if (
                answer === null ||
                typeof answer !== "object" ||
                Array.isArray(answer) ||
                typeof answer.sdp !== "string" ||
                answer.sdp === "" ||
                typeof answer.type !== "string" ||
                answer.type === ""
            ) {
                throw new Error(
                    "Vision offer returned an invalid WebRTC answer",
                );
            }

            if (this.peerConnection !== peerConnection || this.closed) {
                return;
            }

            await peerConnection.setRemoteDescription(answer);
        } catch (error) {
            console.error("WebRTC connection failed", error);

            if (!this.closed) {
                this.setState("error");
                this.scheduleReconnect();
            }
        } finally {
            this.connecting = false;
        }
    }

    scheduleReconnect() {
        if (this.closed || this.reconnectTimer !== null) {
            return;
        }

        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;

            void this.connect();
        }, this.reconnectDelayMs);
    }

    clearReconnect() {
        if (this.reconnectTimer === null) {
            return;
        }

        window.clearTimeout(this.reconnectTimer);

        this.reconnectTimer = null;
    }

    async closePeer() {
        const peerConnection = this.peerConnection;

        this.peerConnection = null;

        if (peerConnection !== null) {
            peerConnection.ontrack = null;
            peerConnection.onconnectionstatechange = null;

            peerConnection.close();
        }

        this.videoElement.srcObject = null;
    }

    async close() {
        if (this.closed) {
            return;
        }

        this.closed = true;

        this.clearReconnect();

        await this.closePeer();

        this.setState("closed");
    }
}
