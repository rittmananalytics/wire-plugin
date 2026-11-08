# Homebrew formula for the Wire CLI (experimental, wire#408).
#
# Lives in the public rittmananalytics/wire-plugin repository as Formula/wire.rb
# is the source of truth, published by the release step with the version and
# sha256 filled in. Install with:
#
#   brew tap rittmananalytics/wire https://github.com/rittmananalytics/wire-plugin
#   brew install wire
#
# The formula installs the packaged CLI and framework under libexec, a Python
# virtualenv with PyYAML (the resolver's one dependency), and the `wire`
# launcher, and on a Mac the standalone agent (wire-agent). It does not
# install OpenAI's codex or Claude Code; `wire doctor` says which are present.

class Wire < Formula
  include Language::Python::Virtualenv

  desc "Wire Framework CLI: the release loop for data platform engagements (experimental)"
  homepage "https://github.com/rittmananalytics/wire"
  url "https://github.com/rittmananalytics/wire-plugin/releases/download/v4.6.3/wire-cli-4.6.3.tar.gz"
  sha256 "76972e4ef386ad8491fd73bf4de938e343f0485977fe4820d1196e461e2bf282"
  license "FSL-1.1-ALv2"

  depends_on "python@3.12"

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/pyyaml-6.0.2.tar.gz"
    sha256 "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e"
  end

  # One block per Mac chip. The release step removes a block when the release
  # ships no agent for that chip, and the formula then installs the CLI only there.
  # >>> wire-agent-darwin-arm64
  on_macos do
    on_arm do
      resource "wire-agent" do
        url "https://github.com/rittmananalytics/wire-plugin/releases/download/v4.6.3/wire-agent-4.6.3-darwin-arm64.tar.gz"
        sha256 "4bb14d1608cb99d735e0d3ec12f92a9a752bd16c91420463806083bd3bc11a98"
      end
    end
  end
  # <<< wire-agent-darwin-arm64
  # >>> wire-agent-darwin-x86_64
  on_macos do
    on_intel do
      resource "wire-agent" do
        url "https://github.com/rittmananalytics/wire-plugin/releases/download/v4.6.3/wire-agent-4.6.3-darwin-x86_64.tar.gz"
        sha256 "ce53b27ada5b14e3d1f4094324f9cd387fd6599eaa5c05b3432f01fd4b10a5a4"
      end
    end
  end
  # <<< wire-agent-darwin-x86_64

  def install
    venv = virtualenv_create(libexec/"venv", "python3.12")
    venv.pip_install resource("pyyaml")
    (libexec/"wire").install Dir["*"]
    if resources.map(&:name).include?("wire-agent")
      # the standalone agent (Codex with Wire's changes; LICENSE, NOTICE and
      # WIRE-CHANGES.txt travel with it), where the CLI looks for it
      resource("wire-agent").stage { (libexec/"wire/bin").install Dir["*"] }
    end
    (bin/"wire").write <<~EOS
      #!/bin/sh
      exec "#{libexec}/venv/bin/python" "#{libexec}/wire/cli/wire.py" "$@"
    EOS
  end

  def caveats
    <<~EOS
      Wire runs its steps through an agent harness: the bundled wire-agent on
      a Mac, or one you install:
        codex   npm install -g @openai/codex
        claude  https://claude.com/claude-code
      Keys go in ~/.wire/secrets.env (see wire/cli/README.md). Run `wire doctor`.
    EOS
  end

  test do
    assert_match "wire #{version}", shell_output("#{bin}/wire version")
  end
end
