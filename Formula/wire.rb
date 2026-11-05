# Homebrew formula for the Wire CLI (experimental, 5.0 alpha, wire#408).
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
  url "https://github.com/rittmananalytics/wire-plugin/releases/download/v5.0.0-alpha.2/wire-cli-5.0.0-alpha.2.tar.gz"
  sha256 "66a79f6f0747f77c1591425a1dc860e0b62e132f3b34e0f8f93024e8adad5546"
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
        url "https://github.com/rittmananalytics/wire-plugin/releases/download/v5.0.0-alpha.2/wire-agent-5.0.0-alpha.2-darwin-arm64.tar.gz"
        sha256 "891b26b86d55101977c0f90bf3af1c43cc7c34b99a4a71234275cdc695e9a300"
      end
    end
  end
  # <<< wire-agent-darwin-arm64
  # >>> wire-agent-darwin-x86_64
  on_macos do
    on_intel do
      resource "wire-agent" do
        url "https://github.com/rittmananalytics/wire-plugin/releases/download/v5.0.0-alpha.2/wire-agent-5.0.0-alpha.2-darwin-x86_64.tar.gz"
        sha256 "f4dcafde509fb87498cdedff7cda0cee12d27c3add641ff5474cf6f2f0d182f5"
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
    assert_match "wire 5.", shell_output("#{bin}/wire version")
  end
end
