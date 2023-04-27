package new

import (
	"path"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/robocorp/robo/cli/config/pyproject"
	"github.com/robocorp/robo/cli/environment"
	"github.com/robocorp/robo/cli/include"
	"github.com/robocorp/robo/cli/paths"
	"github.com/robocorp/robo/cli/rcc"
	"github.com/robocorp/robo/cli/ui"
	"github.com/robocorp/robo/cli/ui/choice"
	"github.com/robocorp/robo/cli/ui/progress"
)

type State int

const (
	StateTemplate State = iota
	StateName
	StateInstall
	StateDone
)

type model struct {
	currentState State

	templates []include.Template
	template  *include.Template
	name      string
	error     error

	templateInput   choice.Model
	nameInput       textinput.Model
	installProgress progress.Model
}

func NewProgram() *tea.Program {
	return tea.NewProgram(initialModel())
}

func initialModel() model {
	templates := include.Templates()
	items := make([]choice.Option, len(templates))
	for i, t := range templates {
		items[i] = choice.Option{
			Title:       t.Name,
			Description: t.Description,
		}
	}

	templateInput := choice.New("Select template", items)

	nameInput := textinput.New()
	installProgress := progress.New()

	m := model{
		templates:       templates,
		templateInput:   templateInput,
		nameInput:       nameInput,
		installProgress: installProgress,
	}

	return m
}

func (m model) Init() tea.Cmd {
	return m.installProgress.PollEvents()
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.Type == tea.KeyCtrlC {
			return m, tea.Quit
		}
	case ui.ErrorMsg:
		m.error = msg
		return m, tea.Quit
	}

	switch m.currentState {
	case StateTemplate:
		return m.updateStateTemplate(msg)
	case StateName:
		return m.updateStateName(msg)
	case StateInstall:
		return m.updateStateInstall(msg)
	case StateDone:
		return m, tea.Quit
	}

	return m, nil
}

func (m model) View() string {
	sections := make([]string, 0)

	// TODO: Move to model/update?
	dirName := paths.SanitizePath(m.nameInput.Value())

	switch m.currentState {
	case StateTemplate:
		sections = append(
			sections,
			m.templateInput.View(),
		)
	case StateName:
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			"Project name:",
			m.nameInput.View(),
			faintText("Directory name:", dirName),
			faintText("\nPress ctrl-c to abort"),
		)
	case StateInstall:
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			section("Project name:", m.name),
			section("Directory name:", dirName),
			m.installProgress.View(),
			faintText("\nPress ctrl-c to abort"),
		)
	case StateDone:
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			section("Project name:", m.name),
			section("Directory name:", dirName),
			m.installProgress.ViewAs(1.0),
			"\nCreated project ✨\n",
		)
	}

	if m.error != nil {
		sections = append(sections, errorBox(m.error))
	}

	return margin.Render(
		lipgloss.JoinVertical(lipgloss.Left, sections...),
	)
}

func (m model) updateStateTemplate(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd
	m.templateInput, cmd = m.templateInput.Update(msg)

	if o := m.templateInput.SelectedOption(); o != nil {
		m.template = m.findTemplateByName(o.Title)
		m.currentState = StateName
		return m, tea.Batch(
			cmd,
			m.nameInput.Focus(),
			textinput.Blink,
		)
	}

	return m, cmd
}

func (m model) updateStateName(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.Type == tea.KeyEnter {
			if value := m.nameInput.Value(); len(value) > 0 {
				m.name = value
				m.currentState = StateInstall
				return m, m.installProject()
			}
		}
	}

	var cmd tea.Cmd
	m.nameInput, cmd = m.nameInput.Update(msg)
	return m, cmd
}

func (m model) updateStateInstall(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg.(type) {
	case progress.ProgressDone:
		m.currentState = StateDone
		return m, tea.Quit
	}

	var cmd tea.Cmd
	m.installProgress, cmd = m.installProgress.Update(msg)
	return m, cmd
}

func (m model) installProject() tea.Cmd {
	ch := m.installProgress.EventChannel()
	onProgress := func(p *rcc.Progress) {
		ch <- progress.ProgressEvent{
			Current: p.Current,
			Total:   p.Total,
			Message: p.Message,
		}
	}

	return func() tea.Msg {
		dir := paths.SanitizePath(m.name)
		if err := m.template.Copy(dir); err != nil {
			return ui.ErrorMsg(err)
		}
		robo, err := pyproject.LoadPath(path.Join(dir, "pyproject.toml"))
		if err != nil {
			return ui.ErrorMsg(err)
		}
		if _, err := environment.EnsureFromConfig(*robo, onProgress); err != nil {
			return ui.ErrorMsg(err)
		}
		return nil
	}
}

func (m model) findTemplateByName(name string) *include.Template {
	for _, t := range m.templates {
		if t.Name == name {
			return &t
		}
	}
	return nil
}
