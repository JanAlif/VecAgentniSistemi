#include "planner.h"

PYBIND11MODULE(planner, m) {
    py::class<planner>(m, "planner")
            .def(py::init<std::vector<std::vector<int>>, bool, bool, bool, float, float>(),
                 py::arg("grid") = std::vector<std::vector<int>>(),
                 py::arg("use_static_cost") = true,
                 py::arg("use_dynamic_cost") = true,
                 py::arg("reset_dynamic_cost") = true,
                 py::arg("decay_factor") = 0.0f,
                 py::arg("density_weight") = 0.0f)
            .def("set_abs_start", &planner::set_abs_start)
            .def("update_path", &planner::update_path)
            .def("get_path", &planner::get_path)
            .def("get_next_node", &planner::get_next_node)
            .def("precompute_penalty_matrix", &planner::precompute_penalty_matrix)
            .def("set_penalties", &planner::set_penalties)
            .def("update_occupations", &planner::update_occupations);
}

<%
cfg['extra_compile_args'] = ['-std=c++17']
setup_pybind11(cfg)
%>